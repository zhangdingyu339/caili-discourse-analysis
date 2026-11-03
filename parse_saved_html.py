"""Extract content from locally saved topic HTML; no network or login required.

Use only pages you are permitted to retain. Output stays private. This is an
offline replacement for the credential-bearing course crawler, not a claim that
the supplied CSV can be regenerated exactly from that incomplete crawler.
"""
from pathlib import Path
import argparse
import csv
import re
from bs4 import BeautifulSoup

def parse_topic(html):
    soup=BeautifulSoup(html,'html.parser')
    rows=[]
    body=soup.select_one('.topic-content')
    if body:
        rows.append({'is_main':1,'text':body.get_text(' ',strip=True)})
    for item in soup.select('li.comment-item'):
        # Select comment body rather than whole comment row (which includes handles).
        body=item.select_one('.reply-content') or item.select_one('p')
        if body:
            for quoted in body.select('.reply-quote, blockquote'):
                quoted.decompose()
            text=body.get_text(' ',strip=True)
            if text:rows.append({'is_main':0,'text':text})
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--html-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('private/parsed.csv'))
    a=p.parse_args()
    if 'private' not in a.output.resolve().parts:
        raise ValueError('Output must be inside a private directory.')
    files=sorted(a.html_dir.glob('*.html'))
    if not files:raise ValueError('No HTML files found.')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['platform','thread_id','is_main','text']);w.writeheader()
        for number,file in enumerate(files):
            # Local sequential IDs avoid exporting original topic URLs/IDs.
            # Each input file must represent one complete topic, not a page fragment.
            for row in parse_topic(file.read_text(encoding='utf-8')):
                w.writerow({'platform':'douban','thread_id':f'local-{number:05d}',**row})
    print('Offline extraction completed. Inspect content privately before analysis.')

if __name__=='__main__':main()
