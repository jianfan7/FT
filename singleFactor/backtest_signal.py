# -*-coding: utf-8 -*-
# Python 3.6
# Author:Zhang Haitao
# Email:13163385579@163.com
# TIME:2018-07-16  09:44
# NAME:FT_hp-backtest_signal.py
import multiprocessing
from functools import partial

# from backtest.main import quick
from config import DIR_SIGNAL, DIR_SINGLE_BACKTEST, DIR_SIGNAL_SMOOTHED
import os
import pandas as pd

START='2010'
END='2015'

SMOOTH_PERIODS=[0,10,20,30,40,50,60,70,80]

def run_backtest(signal, name, directory,start=None,end=None):
    if os.path.exists(directory) and len(os.listdir(directory))>0:
        return # skip
    else:
        os.makedirs(directory)

    results,fig=quick(signal,name,start=start,end=end)

    fig.savefig(os.path.join(directory,name+'.png'))
    for k in results.keys():
        results[k].to_csv(os.path.join(directory,k+'.csv'))



def get_signal_direction(name):
    hret=pd.read_csv(os.path.join(DIR_SIGNAL_SMOOTHED,'raw',name,'hedged_returns.csv'),index_col=0)
    sign=1 if hret.sum()[0]>=0 else -1
    return sign

def get_smoothed_signal(signal,smooth_period):
    if smooth_period==0:
        return signal
    else:
        return signal.rolling(smooth_period,
                                min_periods=int(smooth_period / 2)).mean()

def get_signal(name,smooth):
    if name.endswith('.pkl'):
        fn=name
    else:
        fn=name+'.pkl'

    if isinstance(smooth,str):
        smooth=int(smooth)

    signal=pd.read_pickle(os.path.join(DIR_SIGNAL,fn))
    signal=signal*get_signal_direction(name)
    signal=get_smoothed_signal(signal,smooth)
    return signal

def backtest_raw(name):
    print(name)
    signal = pd.read_pickle(os.path.join(DIR_SIGNAL, name + '.pkl'))
    directory=os.path.join(DIR_SIGNAL_SMOOTHED,'raw',name)
    run_backtest(signal, name, directory,START,END)

def backtest_raw_all():
    fns = os.listdir(DIR_SIGNAL)
    names = [fn[:-4] for fn in fns]
    pool=multiprocessing.Pool(16)
    pool.map(backtest_raw,names)


def backtest_with_smooth(name, smooth_period=0):
    print(name)
    signal=pd.read_pickle(os.path.join(DIR_SIGNAL,name+'.pkl'))
    signal=get_signal_direction(name)*signal

    if smooth_period==0:
        directory=os.path.join(DIR_SIGNAL_SMOOTHED,'0',name)
    else:
        signal=get_smoothed_signal(signal,smooth_period)
        directory=os.path.join(DIR_SIGNAL_SMOOTHED,str(smooth_period),name)

    run_backtest(signal, name, directory,START,END)

def task(args):
    name=args[0]
    smooth_period=args[1]
    backtest_with_smooth(name, smooth_period=smooth_period)

def main():
    fns = os.listdir(DIR_SIGNAL)
    names = [fn[:-4] for fn in fns]
    args=[]
    for sp in SMOOTH_PERIODS:
        for name in names:
            args.append((name,sp))
    pool=multiprocessing.Pool(12)
    pool.map(task,args)


def debug():
    name = 'T__turnover2_std_300'
    backtest_with_smooth(name, 2)
    # backtest_with_smooth(name, 3)
    # backtest_with_smooth(name, 4)


if __name__ == '__main__':
    # backtest_raw_all()
    main()


