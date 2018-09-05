# -*-coding: utf-8 -*-
# Python 3.6
# Author:Zhang Haitao
# Email:13163385579@163.com
# TIME:2018-08-27  21:42
# NAME:FT_hp-a.py

import os
from itertools import combinations

import pandas as pd
# import copy
import matplotlib.pyplot as plt


short='150_iw3_cw2_10_criteria3_150_3'
medium='500_iw2_cw2_10_criteria3_150_2'
long='750_iw2_cw2_3_criteria3_150_2'

directory=r'G:\FT_Users\HTZhang\FT\singleFactor\mixed_signal_backtest'
sets=['short','medium','long']


combs=list(combinations(sets,1))+list(combinations(sets,2))+list(combinations(sets,3))


rets=[]
for comb in combs:
    name='_'.join(comb)
    ss=[]
    for c in comb:
        s = pd.read_csv(os.path.join(directory, eval(c), 'hedged_returns.csv'),
                        index_col=0, header=None).iloc[:, 0]
        # s.name = c
        ss.append(s)
    df=pd.concat(ss,axis=1)
    comret=((1+df).cumprod().mean(axis=1)-1)
    comret.name=name
    rets.append(comret)

rets=pd.concat(rets,axis=1)
rets.plot().get_figure().show()