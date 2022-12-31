from dataclasses import dataclass, asdict, field, fields
from datetime import datetime
import json

@dataclass
class Tick:
    timestamp: float = 0.0
    price: float = 0.0
    volume: float = 0.0
    exchange: str = ""

    @property
    def __dict__(self):
        """
        get a python dictionary
        """
        return asdict(self)

    @property
    def json(self):
        """
        get the json formated string
        """
        return json.dumps(self.__dict__)


# Dataclass to hold BTC Price Information
@dataclass
class BTCPrice:
    ''' Class to hold BTC Price Information'''
    opentime: float = 0.0
    closetime: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    block_height: int = 0

    @property
    def as_csv(self):
        return f"{self.block_height},{self.opentime},{self.closetime},{self.open},{self.high},{self.low},{self.close},{self.volume:.8f}\n"

    @property
    def as_dict(self):
        """
        get a python dictionary
        """
        return {'block_height':int(self.block_height),
                'opentime':int(self.opentime),
                'closetime':int(self.closetime),
                'open':self.open,
                'high':self.high,
                'low':self.low,
                'close':self.close,
                'volume':self.volume}

        return asdict(self)

    @property
    def __dict__(self):
        """
        get a python dictionary
        """
        return asdict(self)

    @property
    def json(self):
        """
        get the json formated string
        """
        return json.dumps(self.__dict__)

    @property
    def as_str(self):
        """
        get a nicely formated string for sending to telegram
        """
        # block_time = datetime.datetime.fromtimestamp(self.time).strftime('%c')
        if self.close > 1.0:
            output = (f"BTC Block Price for block {self.block_height} was:\n"
                      f"Locked on {datetime.fromtimestamp(self.closetime)}\n"
                      f"Open:   {self.open:,.2f} $/₿\n"
                      f"High:   {self.high:,.2f} $/₿\n"
                      f"Low:    {self.low:,.2f} $/₿\n"
                      f"Close:  {self.close:,.2f} $/₿\n"
                      f"Volume: {self.volume:,.8f} ₿\n")
        elif self.close == 0.0:
            output = (f"BTC Block Price for block {self.block_height} was:\n"
                      f"Locked on {datetime.fromtimestamp(self.closetime)}\n"
                      f"Open:   {0.0:,.2f} $/₿\n"
                      f"High:   {0.0:,.2f} $/₿\n"
                      f"Low:    {0.0:,.2f} $/₿\n"
                      f"Close:  {0.0:,.2f} $/₿\n"
                      f"Volume: {self.volume:,.8f} ₿\n")
        else:
            output = (f"BTC Block Price for block {self.block_height} was:\n"
                      f"Locked on {datetime.fromtimestamp(self.closetime)}\n"
                      f"Open:   {1/self.open:,.8f} ₿/$\n"
                      f"High:   {1/self.high:,.8f} ₿/$\n"
                      f"Low:    {1/self.low:,.8f} ₿/$\n"
                      f"Close:  {1/self.close:,.8f} ₿/$\n"
                      f"Volume: {self.volume:,.8f} ₿\n")
        return output

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


# Dataclass to hold BTC Block Timestamp
@dataclass
class BTCBlock(BTCPrice):
    ''' Class to hold BTC Block Information'''
    first_tick: Tick = None
    last_tick: Tick = None
    seen: bool = False
    ticks: list = field(default_factory=list)

    def in_range(self, tick: Tick):
        if tick.timestamp >= self.opentime and tick.timestamp <= self.closetime:
            self.ticks.append(tick)
            return True
        else:
            return False

    def consolidate(self):
        # sort ticks by timestamp
        self.ticks.sort(key=lambda x: x.timestamp, reverse=False)
        if self.first_tick is None:
            earliest = float("inf")
        else:
            earliest = self.first_tick.timestamp
        if self.last_tick is None:
            latest = 0.0
        else:
            latest = self.last_tick.timestamp
        for tick in self.ticks:
            if tick.timestamp < earliest:
                earliest = tick.timestamp
                self.first_tick = tick
                self.open = tick.price
            if tick.timestamp > latest:
                latest = tick.timestamp
                self.last_tick = tick
                self.close = tick.price
            if tick.price > float(self.high):
                self.high = tick.price
            if tick.price < float(self.low):
                self.low = tick.price
            self.volume += tick.volume
        self.ticks = [] # wipe the list to conserve memory

    def get_BTCPrice(self):
        return BTCPrice(opentime=self.opentime,
                        closetime=self.closetime,
                        open=self.open,
                        high=self.high,
                        low=self.low,
                        close=self.close,
                        volume=self.volume,
                        block_height=self.block_height)

    @classmethod
    def from_json(cls, json_string):
        json_data = json.loads(json_string)
        keys = [f.name for f in fields(cls)]
        normal_json_data = {key: json_data[key] for key in json_data if key in keys}
        anormal_json_data = {key: json_data[key] for key in json_data if key not in keys}
        tmp = cls(**normal_json_data)
        for anormal_key in anormal_json_data:
            setattr(tmp, anormal_key, anormal_json_data[anormal_key])
        return tmp

    # Method to read in a file of BTC Block Timestamps
    @classmethod
    def read_file(cls, filename):
        with open(filename, 'r') as f:
            data = f.read()
        return cls.from_json(data)

    # Method to parse a CSV file of BTC Block Timestamps and return a list of BTCBlock objects
    @classmethod
    def parse_csv(cls, filename):
        with open(filename, 'r') as f:
            data = f.read()
        lines = data.splitlines()
        blocks = []
        last_timestamp = 0.0
        for line in lines:
            block, timestamp = line.split(',')
            blocks.append(BTCBlock(block_height=int(block),
                                   closetime=float(timestamp),
                                   opentime=float(last_timestamp)))
            last_timestamp = float(timestamp)
        return blocks



