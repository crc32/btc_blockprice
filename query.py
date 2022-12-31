from dataclasses import dataclass, asdict, field, fields
import json, pickle, bz2, time, os
from indexed_bzip2 import IndexedBzip2File
from Block_Classes import Tick, BTCBlock
start = time.time()
if __name__ == '__main__':
    #btc_blockprice = pickle.load(bz2.BZ2File('btc_blockprice.pkl.bz2', 'rb'))
    #btc_blockprice = pickle.load(lzma.LZMAFile('btc_blockprice.pkl.lzma', 'rb'))
    #btc_blockprice = pickle.load(open('btc_blockprice.pkl', 'rb'))

    #print(btc_blockprice[660000])
    #print(os.cpu_count())
    #with lzma.open('krakenUSD.csv.xz', 'rb') as f:
    with IndexedBzip2File("bp.bz2", parallelization=0) as f:
    #with bz2.BZ2File("bp.bz2", 'rb') as f:
        #f.seek(18036101464)
        json_bytes = f.read()
    json_str = json_bytes.decode('utf-8')
    btc_blockprice = json.loads(json_str)
    print(btc_blockprice['734241'])

    print(f"Time elapsed: {time.time() - start}")

#136101464
# 16310652