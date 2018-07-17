# -*-coding: utf-8 -*-
# Python 3.6
# Author:Zhang Haitao
# Email:13163385579@163.com
# TIME:2018-07-12  14:33
# NAME:FT_hp-beta_daily.py
import os

from config import SINGLE_D_INDICATOR
from data.dataApi import read_local
import pandas as pd
from pandas.tseries.offsets import MonthEnd
import numpy as np
from tools import myroll




trading = read_local('equity_selected_trading_data')
ret = pd.pivot_table(trading, values='pctchange', index='trd_dt',
                     columns='stkcd') / 100
zz500_ret_d = read_local('equity_selected_indice_ir')['zz500_ret_d']
df = pd.concat([zz500_ret_d, ret], axis=1, join='inner')
df = df.dropna(subset=['zz500_ret_d'])
df = df.dropna(how='all')


def save_indicator(df,name):
    df.to_pickle(os.path.join(SINGLE_D_INDICATOR,name+'.pkl'))


def beta(df, d):
    df=df.dropna(thresh=int(d / 2), axis=1)
    df=df.dropna(axis=0)
    # df=df.fillna(0)
    # first column is the market
    X = df.values[:, [0]]
    # prepend a column of ones for the intercept
    X = np.concatenate([np.ones_like(X), X], axis=1)
    # matrix algebra
    b = np.linalg.pinv(X.T.dot(X)).dot(X.T).dot(df.values[:, 1:])
    return pd.Series(b[1], df.columns[1:], name='Beta')


def idioVol(df, d):
    df=df.dropna(thresh=int(d / 2), axis=1)
    df=df.dropna(axis=0)
    # df=df.fillna(0)
    # first column is the market
    X = df.values[:, [0]]
    # prepend a column of ones for the intercept
    X = np.concatenate([np.ones_like(X), X], axis=1)
    # matrix algebra
    b = np.linalg.pinv(X.T.dot(X)).dot(X.T).dot(df.values[:, 1:]) #beta
    resid=df.values[:,1:]-X.dot(b)# real value - fitted value
    resid_std=np.std(resid,axis=0)
    return resid_std

def cal_betas():
    for d in [30,60,180,300]:
        name='T__beta_{}'.format(d)
        results=myroll(df, d).apply(beta, d)
        save_indicator(results,name)
        print(d)

def cal_idioVol():
    for d in [30,60,180,300]:
        name='T__idioVol_{}'.format(d)
        results=myroll(df, d).apply(idioVol, d)
        save_indicator(results,name)
        print(d)