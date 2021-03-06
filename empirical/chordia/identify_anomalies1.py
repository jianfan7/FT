# -*-coding: utf-8 -*-
# Python 3.6
# Author:Zhang Haitao
# Email:13163385579@163.com
# TIME:2018-08-30  16:59
# NAME:FT_hp-identify_anomalies1.py
from collections import OrderedDict
import statsmodels.formula.api as sm

from config import DIR_TMP
from data.dataApi import read_local, get_filtered_ret
from empirical.bootstrap import pricing_assets
from empirical.config_ep import DIR_DM, DIR_CHORDIA, DIR_DM_NORMALIZED, \
    PERIOD_THRESH, DIR_BASEDATA, DIR_YAN
import os
import pandas as pd
from empirical.get_basedata import BENCHS, get_benchmark
from empirical.utils import align_index
from empirical.yan.yan_new import get_realized
from tools import multi_process
import numpy as np
import pickle
import matplotlib.pyplot as plt


#--------------------pricing hedged portfolio--------------------------

#--------------------------------FM regression-------------------------------



#===========================method5: bootstrap==================================
def hurdle_boostrap():
    bench_name= 'capmM'
    # benchmark, assets = get_data(bench_name)
    simulated=pickle.load(open(os.path.join(DIR_YAN, f'{bench_name}_1000.pkl'), 'rb'))

    b_at=simulated['alpha_t']

    realized=get_realized(bench_name)
    r_at=realized['alpha_t']
    c5=b_at.quantile(0.05,axis=1)
    c95=b_at.quantile(0.95,axis=1)
    target=r_at[(r_at<c5) | (c95<r_at)]

    target=target[abs(target)>3]
    len(target)

    indicators=get_prominent_indicators()
    len(indicators)
    len([ind for ind in indicators if ind in target.index])


# if __name__ == '__main__':
#     get_fmt()

#============================================================================================================================

def get_prominent_indicators(critic=3):
    at = pd.concat(
        [pd.read_pickle(os.path.join(DIR_CHORDIA, f'at_{bench}.pkl'))
         for bench in BENCHS], axis=1,sort=True)
    fmt=pd.read_pickle(os.path.join(DIR_CHORDIA,'fmt.pkl'))

    inds1=at[abs(at)>critic].dropna().index.tolist()
    inds2=fmt[abs(fmt)>critic].dropna().index.tolist()
    inds=[ind for ind in inds1 if ind in inds2]
    # len(inds) #26

    # inds1=at[at>CRITIC].dropna().index.tolist()
    # inds2=at[at<-CRITIC].dropna().index.tolist()
    # inds3=fmt[fmt>CRITIC].dropna().index.tolist()
    # inds4=fmt[fmt<-CRITIC].dropna().index.tolist()

    # _get_s=lambda x:pd.read_pickle(os.path.join(DIR_DM,'port_ret','eq',x+'.pkl'))['tb']

    # df=pd.concat([_get_s(ind) for ind in inds],axis=1,keys=inds)
    # df.cumsum().plot().get_figure().show()

    # cr=df.corr().stack().sort_values()
    return inds

#-----------------------------aggregate anomalies------------------------------------------

#=================method 0: select manually=================================
def get_prominent_anomalies0():
    alpha_t = pd.concat(
        [pd.read_pickle(os.path.join(DIR_CHORDIA, f'at_{bench}.pkl'))
         for bench in BENCHS], axis=1,sort=True)
    fmt = pd.read_pickle(os.path.join(DIR_CHORDIA, 'fmt.pkl'))

    CRITIC = 3

    inds1 = alpha_t[alpha_t > CRITIC].dropna().index.tolist()
    inds2 = alpha_t[alpha_t < -CRITIC].dropna().index.tolist()
    inds3 = fmt[fmt > CRITIC].index.tolist()
    inds4 = fmt[fmt < -CRITIC].index.tolist()

    indicators=inds1+inds2
    _get_s=lambda x:pd.read_pickle(os.path.join(DIR_DM,'port_ret','eq',x+'.pkl'))['tb']

    df=pd.concat([_get_s(ind) for ind in indicators],axis=1,keys=indicators)
    # df.cumsum().plot().get_figure().show()

    cr=df.corr().stack().sort_values()

    test_indicators=abs(cr).sort_values().index[0]

    myfactors=df[list(test_indicators)]
    return myfactors

def get_at_manuallymodel():
    ff3=get_benchmark('ff3M')
    myfactors=get_prominent_anomalies0()
    manually=pd.concat([ff3,myfactors],axis=1).dropna()

    results=pricing_all_factors(manually,'manually')
    results.to_pickle(os.path.join(DIR_CHORDIA,'at_manually.pkl'))

    #compare
    alpha_t = pd.concat(
        [pd.read_pickle(os.path.join(DIR_CHORDIA, f'at_{bench}.pkl'))
         for bench in BENCHS], axis=1,sort=True)
    at_my=pd.read_pickle(os.path.join(DIR_CHORDIA,'at_mymodel.pkl'))
    (abs(alpha_t)>3).sum()
    (abs(at_my)>3).sum()

#=================method3: cluster=========================

#==================method4: PLS============================

#==================================================================================================

#TODO: we should check absolute tvalue, since these signals are generated randomly, being negative or positive does not make any sense.

'''
1. 有些指标样本太少
2. fm 中的指标

'''






def main():
    # get_alpha_t_for_all_bm()
    calculate_fmt()
    get_fmt()




