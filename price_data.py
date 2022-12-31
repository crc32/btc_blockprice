import pickle, bz2, time, os, asyncio
from indexed_bzip2 import IndexedBzip2File
from Block_Classes import Tick, BTCBlock, BTCPrice
import logging
import httpx
import subprocess

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

# Grab External settings
with open("config.toml", mode="rb") as fp:
    config = tomllib.load(fp)

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(filename)s : %(lineno)d - %(levelname)s - %(message)s", level=logging.DEBUG
)


async def download_price_data():
    # download data from bitcoincharts.com
    async with httpx.AsyncClient(verify=False) as client:
        for exchange in ['bitstampUSD', 'coinbaseUSD', 'krakenUSD']:
            logger.debug(f"Downloading {exchange}")
            response = await client.get(f"{config['general']['price_data_url']}{exchange}.csv.gz")
            with open(f"{exchange}.csv.gz", "wb") as f:
                f.write(response.content)
    reframe = ['ls *.gz | parallel "gunzip -c {} | pbzip2 -c > {.}.bz2"']

def recompress():
    subprocess.run('ls *.gz | parallel "gunzip -c {} | pbzip2 -c > {.}.bz2"', shell=True)

# print a list of BTCPrice objects to csv
def print_price_data_to_csv(data, filename):
    with open(filename, 'w') as f:
        f.write("block_height,opentime,closetime,open,high,low,close,volume\n")
        for price in data:
            f.write(price.as_csv)


def calc_blocks(return_data: bool = False):
    btc_timestamps = BTCBlock.parse_csv("timestamps.txt")
    bzfiles = ['mtgoxUSD.csv.bz2', 'bitstampUSD.csv.bz2', 'coinbaseUSD.csv.bz2', 'krakenUSD.csv.bz2']
    for file in bzfiles:
        btc_iterator = iter(btc_timestamps)
        current_block = next(btc_iterator)
        exhausted = False
        final_blockheight = 0
        print(f"Processing {file}")
        with IndexedBzip2File(file, parallelization=os.cpu_count()) as f:
            for line in enumerate(f):
                if exhausted: continue
                line_array = line[1].decode('utf-8').strip().split(',')  # needed for gzipped files
                temp_tick = Tick(timestamp=float(line_array[0]),
                                 price=float(line_array[1]),
                                 volume=float(line_array[2]),
                                 exchange=file[0:-4])
                if temp_tick.timestamp < 1270000000: continue  # ignore spurious data before 2010
                if current_block.in_range(temp_tick):
                    continue
                else:
                    while not current_block.in_range(temp_tick):
                        current_block.consolidate()
                        last_close = current_block.close
                        try:
                            final_blockheight = current_block.block_height
                            current_block = next(btc_iterator)
                        except StopIteration:
                            exhausted = True
                            break
                        if not current_block.seen:
                            current_block.opn = last_close
                            current_block.close = last_close
                            current_block.high = last_close
                            current_block.low = last_close
                            current_block.seen = True

    # step back 10 blocks to ensure when we add more later there isn't a time-frame discrepancy
    print_price_data_to_csv(btc_timestamps[0:final_blockheight - 10], "test.csv")

    temp_btc_blockprice = {}
    for id, block in enumerate(btc_timestamps[0:final_blockheight - 10]):
        if (block.block_height > 700000 and block.opn == 0.0): continue
        temp_btc_blockprice[block.block_height] = block.as_dict
    pickle.dump(temp_btc_blockprice, bz2.BZ2File("btc_blockprice.pkl.bz2", "wb"))

    if return_data:
        return btc_blockprice
    else:
        return None


async def get_block_info(height: int):
    async with httpx.AsyncClient(verify=False) as client:
        resp_hash = await client.get(f"{config['general']['mempool_url']}"
                                     f"{config['general']['block_height_api']}"
                                     f"{str(height)}")
        block_hash = resp_hash.content.decode("utf-8")
        block_info = await client.get(f"{config['general']['mempool_url']}"
                                      f"{config['general']['block_info_api']}"
                                      f"{block_hash}")
    block_info_dict = block_info.json()
    try:
        block_info_dict["extras"].pop("coinbaseTx", True)
    except KeyError:
        pass
    return {height: block_info_dict}


def write_to_disk(height: int, data):
    fn = (height // 100000) * 100000
    with open("./block_info/block_" + str(fn) + ".txt", "a") as f:
        json.dump(data, f)
        f.write("\n")


def write_timestamp(height: int, epochtime: int):
    with open("./timestamps.txt", "a") as f:
        f.write(str(height) + "," + str(epochtime) + "\n")


async def get_block_tip():
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(f"{config['general']['mempool_url']}"
                                f"{config['general']['block_tip_api']}")
    btc_timestamps = BTCBlock.parse_csv("timestamps.txt")
    return (btc_timestamps[-1].block_height, int(resp.content.decode("utf-8")))


async def load_new_timestamps():
    # get the current block height, then back off by 15 to ensure that
    # a reorg doesn't break our data
    our_tip, block_tip = await get_block_tip()
    for block_height in range(our_tip + 1, block_tip - 15):
        data_temp = await get_block_info(block_height)
        # write_to_disk(block_height, data_temp)
        write_timestamp(block_height, data_temp[block_height]['timestamp'])
        # if block_height % 5000 == 0: print(block_height)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    start = time.time()

    # btc_blockprice = calc_blocks(True)

    # print(btc_blockprice[700000])
    #asyncio.get_event_loop().run_until_complete(download_price_data())
    # print(asyncio.get_event_loop().run_until_complete(get_block_tip()))
    #asyncio.get_event_loop().run_until_complete(load_new_timestamps())
    asyncio.get_event_loop().run_until_complete(download_price_data())
    recompress()
    calc_blocks(False)

    print(f"Time elapsed: {time.time() - start}")
