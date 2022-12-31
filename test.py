from dataclasses import dataclass, asdict, field, fields
import json, time
import datetime
import gzip, io

@dataclass
class test_class:
    value: float = 0.0



if __name__ == '__main__':
    tempA = test_class(value=1.0)
    tempB = [test_class(value=1.0), test_class(value=312.0), test_class(value=123.0)]
    print(tempA)
    print(tempB)
    b = iter(tempB)
    g = next(b)
    g.value = 555.0
    print(tempB)
    with gzip.GzipFile('krakenUSD.csv.gz', 'r') as z:
        for line in enumerate(z):
            print(line[1].decode('utf-8').strip())
    #with zipfile.ZipFile(...) as z:
    #    with z.open(...) as f:
    #        for line in f:
    #            print
    #            line
