import pysmaplus as pysma
from typing import TYPE_CHECKING, Any
import aiohttp


async def identify(url: str, savedebug: bool) -> list:
    order_list = ["found", "maybe", "failed"]
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=False)
    ) as session:
        ret = await pysma.autoDetect(session, url)
        ret_sorted = sorted(ret, key=lambda x: order_list.index(x.status))
        return ret_sorted


async def discoveryAndScan():
    debug: dict[str, Any] = {"discovery": [], "status": {}}
    ret = await pysma.discovery()
    if len(ret) == 0:
        debug["status"] = "Found no SMA devices via speedwire discovery request!"
    #      debug["addr"] = ret

    for r in ret:
        z = {"addr": r[0], "port": r[1], "identify": []}
        debug["discovery"].append(z)
        # print(r[0])
        ident = await identify(r[0], False)
        for i in ident:
            z["identify"].append(
                {
                    "access": i.access,
                    "status": i.status,
                    "tested_endpoints": i.tested_endpoints,
                    "exception": str(i.exception),
                    "remark": i.remark,
                    "device": i.device,
                }
            )
    return debug
