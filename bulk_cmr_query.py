import requests
import math
import aiohttp
import asyncio
import datetime
import os
import aiofiles

from aiohttp import BasicAuth

from typing import Sequence, Tuple, Optional, List
from netrc import netrc

CMR_OPS = "https://cmr.earthdata.nasa.gov/search" # CMR API Endpoint
URS = 'urs.earthdata.nasa.gov' # Address to call for authentication

_DatetimeRangeT = Tuple[datetime.datetime, datetime.datetime]


def get_cmr_pages_urls(
    base_url: str,
    collections: Sequence[str], 
    datetime_range: _DatetimeRangeT,
    page_size: int = 10
) -> Optional[Sequence[str]]:
    if isinstance(collections, str): # Sequence[str] is str == True
        collections = [collections]
    
    temporal = ','.join(list(map(lambda x: x.strftime("%Y-%m-%dT%H:%M:%SZ"), datetime_range)))

    response = requests.get(
        base_url,
        params={
            'concept_id': list(collections),
            'temporal': temporal,
            'page_size': page_size
        },
        headers={
            'Accept': 'application/json'
        }
    )
    if response.status_code != 200:
        print(f"Request for collections: {collections} failed. Status code: {response.status_code}")
        return None
    
    hits = int(response.headers['CMR-Hits'])
    n_pages = math.ceil(hits / page_size)
    return [
        f"{response.url}&page_num={x}".replace('granules?', 'granules.json?')
        for x in list(range(1, n_pages + 1))
    ]


def get_tasks(
    session: aiohttp.ClientSession,
    base_url: str,
    collections: Sequence[str],
    datetime_range: _DatetimeRangeT,
    page_size: int
) -> List[aiohttp.client._RequestContextManager]:
    tasks = []

    urls = get_cmr_pages_urls(base_url, collections, datetime_range, page_size)

    for l in urls:
        tasks.append(session.get(l))
    
    return tasks


async def get_urls(
    session: aiohttp.ClientSession,
    base_url: str,
    collections: Sequence[str],
    datetime_range: _DatetimeRangeT,
    page_size: int = 10
) -> List[str]:
    result = []
    tasks = get_tasks(session, base_url, collections, datetime_range, page_size)
    responses = await asyncio.gather(*tasks)
    for response in responses:
        res = await response.json()
        # TODO: Code could be cleaner
        result.extend([
            l['href']
            for g in res['feed']['entry']
            for l in g['links']
            if 'https' in l['href'] and l['href'].endswith('.h5')
        ])

    return result


async def download_file(
    session: aiohttp.ClientSession,
    url: str,
) -> None:
    async with session.get(url) as resp:
        if resp.status != 200:
            print(f"Failed to fetch file from url: {url}")
            return
        
        async with aiofiles.open(f"data/{url.split('/')[-1]}", 'wb+') as file:
            count = 0
            while True:
                chunk = await resp.content.read(16 * 1024)
                if not chunk:
                    break
                print(f"Writing chunk {count} for data/{url.split('/')[-1]}")
                await file.write(chunk)
                count += 1


async def main() -> None:
    url = f'{CMR_OPS}/{"granules"}'

    collections = ['C1373412034-LPDAAC_ECS']
    datetime_range = (
        datetime.datetime(year=2021, month=10, day=17),
        datetime.datetime(year=2021, month=10, day=19),
    )

    async with aiohttp.ClientSession() as session:
        results = await get_urls(session, url, collections, datetime_range, page_size=10)
        print(f"Number of files to download: {len(results)}")

    # Make sure user is authenticated before even trying to download the different files
    try:
        netrc_dir = os.path.expanduser("~/.netrc")
        netrc(netrc_dir).authenticators(URS)[0]
    except (FileNotFoundError, TypeError):
        print("Failed to authenticate. Please the earthdata_login.py script first to generate credentials")
        return 

    username, _, password = netrc(netrc_dir).authenticators(URS)

    async with aiohttp.ClientSession(
        auth=BasicAuth(login=username, password=password)
    ) as session:
        tasks = []
        for url in results[:5]: # Avoid downloading too many files
            tasks.append(asyncio.create_task(download_file(session, url)))

        await asyncio.gather(*tasks)
    

if __name__ == "__main__":
    asyncio.run(main())