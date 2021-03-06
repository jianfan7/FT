# -*-coding: utf-8 -*-
# Python 3.6
# Author:Zhang Haitao
# Email:13163385579@163.com
# TIME:2018-07-07  17:11
# NAME:FT-backtest_cz.py
import multiprocessing

from config import SINGLE_D_INDICATOR, DIR_SIGNAL, DIR_SINGLE_BACKTEST, \
    LEAST_CROSS_SAMPLE
import os
import pandas as pd
from data.dataApi import read_local
from backtest.main import quick
from tools import clean


def test_one(name):
    print(name)
    df = pd.read_pickle(os.path.join(SINGLE_D_INDICATOR, name + '.pkl'))
    df=df.stack().to_frame().swaplevel().sort_index()
    df.index.names=['stkcd','trd_dt']
    df.columns=[name]
    fdmt = read_local('equity_fundamental_info')
    data=pd.concat([fdmt,df],axis=1,join='inner')

    data=data.dropna(subset=['type_st','young_1year'])
    data = data[(~data['type_st']) & (~ data['young_1year'])]  # 剔除st 和上市不满一年的数据
    data=data.dropna(subset=['wind_indcd',name])
    data=data.groupby('trd_dt').filter(lambda x:x.shape[0]>LEAST_CROSS_SAMPLE)


    cleaned_data=clean(data,col=name,by='trd_dt')
    signal=pd.pivot_table(cleaned_data,values=name,index='trd_dt',columns='stkcd').sort_index()
    signal=signal.shift(1)#trick:

    directory=os.path.join(DIR_SINGLE_BACKTEST, name)
    if not os.path.exists(directory):
        os.makedirs(directory)
    signal.to_csv(os.path.join(directory, 'signal.csv'))

    # directory=os.path.join(DIR_SINGLE_BACKTEST,name)
    # signal=pd.read_csv(os.path.join(directory,'signal.csv'),index_col=0,parse_dates=True)

    start='2010'
    results,fig=quick(signal,name,start=start)

    fig.savefig(os.path.join(directory,name+'.png'))
    for k in results.keys():
        results[k].to_csv(os.path.join(directory,k+'.csv'))

def task(name):
    try:
        print('Starting:  {}'.format(name))
        test_one(name)
    except:
        print('Wrong------------>{}'.format(name))

def test_all():
    # path = 'indicators.xlsx'
    # df = pd.read_excel(path, sheet_name='valid')
    # names=df['name']
    fns=os.listdir(SINGLE_D_INDICATOR)
    names=[fn[:-4] for fn in fns]
    print(len(names))
    checked=[fn for fn in os.listdir(DIR_SINGLE_BACKTEST)]
    names=[n for n in names if n not in checked]
    print(len(names))
    pool = multiprocessing.Pool(4)
    pool.map(task, names)

    # for i,name in enumerate(names):
    #     try:
    #         backtest_with_smooth(name)
    #         print(i,name)
    #     except:
    #         pass

def debug():
    name='Q__roe'
    task(name)

if __name__ == '__main__':
    test_all()


#debug: G__divdend3YR

#TODO:analyse the characteristics of the distribution

#TODO if the relative return is negative, revert the signal
#TODO: 1. smooth;(before signal or afeter signal) 2. out-of-sample( 2010-2015);


#TODO:3. weight of signal

#TODO： hit rate
#TODO: analyse the distribution of the hedged returns



'''
1. short leg should also be employed to filter the signal. If any stock belong to 
a short leg, we should be cautious about these stocks.

2. bid/ask spread, price impact of large trades, 

3. transaction cost is different for different stocks, it can be based on many
    characteristics, for example, size,idiosyncratic volatitlity and so on.


'''