import tempfile
import unittest
from pathlib import Path
import pandas as pd
from analysis import clean_text,load_corpus,classify_platform,run
from parse_saved_html import parse_topic

class AnalysisChecks(unittest.TestCase):
    def test_normalization_and_cross_platform_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.csv'
            pd.DataFrame({'text':['彩礼与婚姻讨论 https://example.com','彩礼与婚姻讨论','短'],
                          'platform':['douban','tieba','douban'],
                          'topic_id':['1','2','3']}).to_csv(p,index=False)
            data,audit=load_corpus(p)
            self.assertEqual(len(data),1)
            self.assertEqual(audit['normalized_duplicates_removed'],1)
            self.assertEqual(audit['short_or_empty_removed'],1)
            self.assertNotIn('http',data.iloc[0]['text'])

    def test_requires_thread_identifiers(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.csv';pd.DataFrame({'text':['彩礼与婚姻讨论']}).to_csv(p,index=False)
            with self.assertRaises(ValueError):load_corpus(p)

    def test_single_platform_does_not_invent_classification(self):
        data=pd.DataFrame({'platform':['douban'],'text':['彩礼与婚姻讨论'],'group':['douban:1']})
        self.assertEqual(classify_platform(data,Path('.'))['status'],'not_run')

    def test_real_output_cannot_enter_public_results(self):
        with self.assertRaises(ValueError):run('nonexistent.csv','results',demo=False)

    def test_group_disjoint_two_platform_smoke(self):
        # Synthetic fixture tests execution only; its score is not research evidence.
        rows=[]
        for platform,word in [('douban','房贷'),('tieba','嫁妆')]:
            for thread in range(10):
                for comment in range(2):
                    rows.append(dict(platform=platform,group=f'{platform}:{thread}',
                                     text=f'彩礼 婚姻 财产 协议 {word} 讨论 ' + '风险 '*comment))
        with tempfile.TemporaryDirectory() as d:
            result=classify_platform(pd.DataFrame(rows),Path(d))
            self.assertEqual(result['status'],'completed')
            self.assertEqual(result['train_threads']+result['test_threads'],20)

    def test_html_content_excludes_author_block_and_quoted_reply(self):
        html='''<div class="topic-content">彩礼讨论正文</div>
        <li class="comment-item"><a class="author">PRIVATE_AUTHOR</a>
        <p class="reply-content"><span class="reply-quote">PRIVATE_QUOTE</span>房贷需要协议</p></li>'''
        rows=parse_topic(html)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[1]['text'],'房贷需要协议')

if __name__=='__main__':unittest.main()
