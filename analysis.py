"""Offline Chinese discourse analysis; no raw social posts are published."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import unicodedata
import importlib.metadata

import jieba
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.dummy import DummyClassifier

SEED = 42
FRAMES = {
    'gender_roles': ['男性','女性','男人','女人','丈夫','妻子','父权','性别','冠姓权','随母姓','入赘'],
    'conflict_language': ['对立','歧视','攻击','侮辱','争吵','骂','羞辱','敌视'],
    'asset_risk': ['首付','房贷','贷款','公积金','婚前财产','财产分割','协议','加名','买房','房产','风险'],
}
STOPWORDS = set('的 了 是 在 和 也 就 都 我 你 他 她 我们 你们 他们 她们 一个 这个 那个 什么 怎么 为什么 但是 因为 所以 还是 可以 没有 不是 觉得 真的 已经 这种 这样 那样 可能 如果 自己 时候 然后 现在 只是 就是 以及 对于 进行 还有 很多 一些'.split())
for words in FRAMES.values():
    for word in words:
        jieba.add_word(word)

def clean_text(value):
    """Normalize text without claiming that this fully anonymizes social posts."""
    value = unicodedata.normalize('NFKC', str(value or ''))
    value = re.sub(r'https?://\S+|www\.\S+', ' ', value)
    value = re.sub(r'@[\w\u4e00-\u9fff-]+', ' ', value)
    value = re.sub(r'<[^>]*>', ' ', value)
    value = re.sub(r'\b\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()

def tokenize(value):
    return [t for t in jieba.lcut(value) if re.fullmatch(r'[\u4e00-\u9fff]{2,}', t) and t not in STOPWORDS]

def load_corpus(path, default_platform='douban'):
    source = pd.read_csv(path, dtype=str).fillna('')
    if 'text' not in source:
        raise ValueError('CSV requires a text column.')
    platform = source['platform'] if 'platform' in source else pd.Series(default_platform, index=source.index)
    thread_column = next((c for c in ['thread_id','topic_id'] if c in source), None)
    if not thread_column:
        raise ValueError('CSV requires thread_id or topic_id; thread grouping must not be invented.')
    data = pd.DataFrame({'platform':platform.str.strip().str.lower(),
                         'thread_id':source[thread_column].str.strip(),
                         'text':source['text'].map(clean_text)})
    if (data['platform']=='').any() or (data['thread_id']=='').any():
        raise ValueError('Platform and thread identifiers must be present.')
    original_rows = len(data)
    original_threads = data[['platform','thread_id']].drop_duplicates().shape[0]
    short = data['text'].str.len() < 5
    data = data.loc[~short].copy()
    # Drop repeated text across the entire corpus before splitting.
    duplicate_count = int(data['text'].duplicated().sum())
    data = data.drop_duplicates('text').reset_index(drop=True)
    data['group'] = data['platform'] + ':' + data['thread_id']
    audit = dict(input_rows=original_rows,input_threads=original_threads,
                 short_or_empty_removed=int(short.sum()),normalized_duplicates_removed=duplicate_count,
                 retained_rows=len(data),retained_threads=int(data['group'].nunique()),
                 platform_count=int(data['platform'].nunique()))
    return data, audit

def vectorizer():
    return TfidfVectorizer(tokenizer=tokenize,token_pattern=None,lowercase=False,
                           min_df=2,max_df=0.95,max_features=5000)

def analyze_topics(data, output, topics=5):
    tfidf = vectorizer()
    try:
        X = tfidf.fit_transform(data['text'])
    except ValueError as error:
        raise ValueError('Too few usable repeated Chinese terms for topic modeling.') from error
    count = min(topics,X.shape[0],X.shape[1])
    if count < 2:
        raise ValueError('At least two usable topic components are required.')
    model = NMF(n_components=count, init='nndsvda', random_state=SEED,max_iter=1000)
    weights = model.fit_transform(X)
    totals = weights.sum(axis=1,keepdims=True)
    proportions = np.divide(weights,totals,out=np.zeros_like(weights),where=totals>0)
    terms = np.asarray(tfidf.get_feature_names_out())
    # These vocabulary outputs stay private for real data.
    pd.DataFrame([{'topic':i,'top_terms':' | '.join(terms[np.argsort(row)[-10:][::-1]])}
                  for i,row in enumerate(model.components_)]).to_csv(output/'topics.csv',index=False)
    shares = pd.DataFrame(proportions,columns=[f'topic_{i}' for i in range(count)])
    shares['platform'] = data['platform'].values
    means = shares.groupby('platform').mean()
    means.to_csv(output/'topic_means.csv')
    ax=means.T.plot.bar(figsize=(8,4),rot=0)
    ax.set(ylabel='Mean normalized NMF weight',xlabel='Topic',
           title='Exploratory topic weights (descriptive)')
    ax.figure.tight_layout();ax.figure.savefig(output/'topic_shares.png',dpi=140);plt.close(ax.figure)
    return {'topics':count,'zero_topic_weight_documents':int((totals==0).sum())}

def analyze_frames(data, output):
    rows=[]
    for platform, subset in data.groupby('platform'):
        for frame, words in FRAMES.items():
            hits=np.asarray([sum(text.count(word) for word in words) for text in subset['text']])
            lengths=np.asarray([max(1,len(re.findall(r'[\u4e00-\u9fff]',t))) for t in subset['text']])
            rows.append(dict(platform=platform,frame=frame,documents=len(subset),
                activation_rate=float((hits>0).mean()),zero_rate=float((hits==0).mean()),
                mean_hits_per_100_chinese_chars=float((100*hits/lengths).mean())))
    table=pd.DataFrame(rows);table.to_csv(output/'frame_summary.csv',index=False)
    return table

def classify_platform(data, output):
    """Fixed baseline model; thread-disjoint split and training-only vocabulary."""
    if data['platform'].nunique()!=2:
        return {'status':'not_run','reason':'Requires exactly two observed platforms; no labels are fabricated.'}
    # Try fixed seeded splits until each side contains both platforms.
    splitter=GroupShuffleSplit(n_splits=30,test_size=0.2,random_state=SEED)
    split=None
    for train,test in splitter.split(data,groups=data['group']):
        if data.iloc[train]['platform'].nunique()==2 and data.iloc[test]['platform'].nunique()==2:
            split=(train,test);break
    if split is None:
        raise ValueError('Not enough independent threads for a two-platform holdout.')
    train,test=split
    assert set(data.iloc[train]['group']).isdisjoint(data.iloc[test]['group'])
    train_data=data.iloc[train];test_data=data.iloc[test]
    model=Pipeline([('tfidf',vectorizer()),('classifier',LogisticRegression(max_iter=2000,random_state=SEED))])
    model.fit(train_data['text'],train_data['platform'])
    baseline=DummyClassifier(strategy='most_frequent').fit(np.zeros((len(train),1)),train_data['platform'])
    rows=[]
    for name,pred in [('TF-IDF + logistic regression',model.predict(test_data['text'])),
                       ('Majority baseline',baseline.predict(np.zeros((len(test),1))))]:
        rows.append(dict(model=name,accuracy=float(accuracy_score(test_data['platform'],pred)),
                         balanced_accuracy=float(balanced_accuracy_score(test_data['platform'],pred)),
                         macro_f1=float(f1_score(test_data['platform'],pred,average='macro'))))
    pd.DataFrame(rows).to_csv(output/'platform_classification.csv',index=False)
    return dict(status='completed',train_rows=len(train),test_rows=len(test),
                train_threads=int(train_data['group'].nunique()),test_threads=int(test_data['group'].nunique()))

def run(input_path,output_path,demo=False,default_platform='douban'):
    output=Path(output_path).resolve()
    if not demo and 'private' not in output.parts:
        raise ValueError('Real-data output must be inside a directory named private to prevent accidental publication.')
    output.mkdir(parents=True,exist_ok=True)
    if demo:
        fixture=pd.read_csv(input_path).fillna('')
        if 'synthetic' not in fixture or not fixture['synthetic'].astype(str).str.lower().isin(['true','1']).all():
            raise ValueError('Demo mode requires an explicitly labeled synthetic fixture.')
    data,audit=load_corpus(input_path,default_platform)
    if len(data)<10:raise ValueError('At least 10 retained texts are required.')
    metadata={'data_kind':'synthetic_demo' if demo else 'private_observed_data',
              'input_sha256':hashlib.sha256(Path(input_path).read_bytes()).hexdigest(),
              'seed':SEED,'audit':audit,'topic_model':analyze_topics(data,output),
              'classification':classify_platform(data,output),
              'packages':{p:importlib.metadata.version(p) for p in ['numpy','pandas','scikit-learn','jieba','matplotlib']}}
    analyze_frames(data,output)
    (output/'run_metadata.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+'\n')
    return metadata

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('private/results'))
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--platform',default='douban')
    args=parser.parse_args()
    result=run(args.input,args.output,args.demo,args.platform)
    print(json.dumps({'data_kind':result['data_kind'],'audit':result['audit'],
                      'classification':result['classification']},indent=2))
