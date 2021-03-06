# -*-coding: utf-8 -*-
# Python 3.6
# Author:Zhang Haitao
# Email:13163385579@163.com
# TIME:2018-06-23  21:11
# NAME:FT-check.py
import multiprocessing
import pickle

from data.dataApi import read_local
import pandas as pd
import os
from config import SINGLE_D_INDICATOR, SINGLE_D_CHECK, DCC, \
    FORWARD_TRADING_DAY
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from tools import monitor, filter_st_and_young, clean

G = 10


#review: alternative method
'''
idea:
    1. build a mould by use daily trading data
    2. put all the data into the mould
      dfs to put in mould:
        1) three sheet
        2) trading data
        3) div_cash data
    3. ffill with a limit
    4. calculate new indicator
    5. filter with st and young_1year
    6. output


'''

def change_index(df):
    df = df.reset_index().sort_values(['stkcd', 'trd_dt', 'report_period'])
    # 如果在相同的trd_dt有不同的report_period记录，取report_period较大的那条记录
    df = df[~df.duplicated(['stkcd', 'trd_dt'], keep='last')]
    del df['report_period']
    df=df.set_index(['stkcd','trd_dt']).dropna()
    return df

def get_cover_rate(monthly, col):
    monthly['g'] = monthly.groupby('month_end', group_keys=False).apply(
        lambda x: pd.qcut(x['cap'], G,
                          labels=['g{}'.format(i) for i in range(1, G + 1)]))

    cover_rate = monthly.groupby(['month_end', 'g']).apply(
        lambda x: x[col].notnull().sum() / x.shape[0])
    cover_rate = cover_rate.unstack('g') / G
    cover_rate = cover_rate[['g{}'.format(i) for i in range(1, G + 1)]]
    return cover_rate

def get_beta_t_ic(df,col_factor,col_ret):
    '''
    df: DataFrame
        第一列为收益率，第二列为因子值

    计算因子收益率、t值、秩相关系数（IC值）
    '''

    x=df[col_factor]
    y=df[col_ret]
    sl = stats.linregress(x, y)
    beta = sl.slope
    tvalue = sl.slope / sl.stderr
    ic = stats.spearmanr(df)[0]
    return pd.Series([beta,tvalue,ic],index=['beta','tvalue','ic'])

def beta_t_ic_describe(beta_t_ic):
    '''
    beta_t_ic: DataFrame
        含有return, tvalue, ic
    '''
    describe = {
                'Return Mean': beta_t_ic.beta.mean(),
                'months':beta_t_ic.shape[0],
                'Return Std': beta_t_ic.beta.std(),
                'P(t > 0)': len(beta_t_ic[beta_t_ic.tvalue > 0]) / len(beta_t_ic),
                'P(t > 2)': len(beta_t_ic[beta_t_ic.tvalue > 2]) / len(beta_t_ic),
                'P(t <- 2)': len(beta_t_ic[beta_t_ic.tvalue <- 2]) / len(beta_t_ic),
                't Mean': beta_t_ic.tvalue.mean(),
                'rank IC Mean': beta_t_ic.ic.mean(),
                'rank IC Std': beta_t_ic.ic.std(),
                'P(rank IC > 0)': len(beta_t_ic[beta_t_ic.ic > 0]) / len(beta_t_ic.ic),
                'P(rank IC > 0.02)': len(beta_t_ic[beta_t_ic.ic > 0.02]) / len(beta_t_ic.ic),
                'P(rank IC <- 0.02)': len(beta_t_ic[beta_t_ic.ic <- 0.02]) / len(beta_t_ic.ic),
                'rank IC IR': beta_t_ic.ic.mean() / beta_t_ic.ic.std(),
                'tvalue':beta_t_ic.beta.mean()*sqrt(beta_t_ic.shape[0])/beta_t_ic.beta.std()
                }
    describe=pd.Series(describe)
    return describe

def plot_beta_t_ic(beta_t_ic):
    fig = plt.figure(figsize=(16, 8))

    ax1 = plt.subplot(211)
    ax1.bar(beta_t_ic.index, beta_t_ic['beta'], width=20,color='b')
    ax1.set_ylabel('return bar')
    ax1.set_title('factor return')

    ax4=ax1.twinx()
    ax4.plot(beta_t_ic.index,beta_t_ic['beta'].cumsum(),'r-')
    ax4.set_ylabel('cumsum',color='r')
    [tl.set_color('r') for tl in ax4.get_yticklabels()]

    ax2 = plt.subplot(223, sharex=ax1)
    ax2.bar(beta_t_ic.index, beta_t_ic['tvalue'], width=20,color='olive')
    ax2.axhline(y=2, linewidth=1, marker='_', color='r')
    ax2.axhline(y=-2, linewidth=1, marker='_', color='r')
    ax2.set_title('tvalue')

    ax3 = plt.subplot(224, sharex=ax1)
    ax3.bar(beta_t_ic.index, beta_t_ic['ic'], width=20)
    ax3.set_title('ic')
    plt.close()
    return fig

def drawdown(x):
    '''
    Parametes
    =========
    x: DataFrame
        净值数据
    '''
    drawdown = []
    for t in range(len(x)):
        max_t = x[:t + 1].max()
        drawdown_t = min(0, (x[t] - max_t) / max_t)
        drawdown.append(drawdown_t)
    return pd.Series(drawdown).min()

def g_ret_describe(g_ret):
    nav = (1 + g_ret).cumprod()
    hpy = nav.iloc[-1, :] - 1
    annual = (nav.iloc[-1, :]) ** (12 / len(g_ret)) - 1
    sigma = g_ret.std() * sqrt(12)
    sharpe = (annual - 0.036) / sigma
    max_drdw = nav.apply(drawdown)

    rela_retn = g_ret.sub(g_ret.iloc[:, -1], axis='index')
    rela_nav = (1 + rela_retn).cumprod()
    rela_annual = (rela_nav.iloc[-1, :]) ** (12 / len(rela_retn)) - 1
    rela_sigma = rela_retn.std() * sqrt(12)
    rela_retn_IR = rela_annual / rela_sigma
    rela_max_drdw = rela_nav.apply(drawdown)

    return pd.DataFrame({
                'hpy': hpy,
                'annual': annual,
                'sigma': sigma,
                'sharpe': sharpe,
                'max_drdw': max_drdw,
                'rela_annual': rela_annual,
                'rela_sigma': rela_sigma,
                'rela_ret_IR': rela_retn_IR,
                'rela_max_drdw': rela_max_drdw})

def plot_layer_analysis(g_ret, g_ret_des,cover_rate):
    fig = plt.figure(figsize=(16, 8))
    ax1 = plt.subplot(221)
    logRet = np.log((1 + g_ret).cumprod())
    for col in logRet.columns:
        if col == 'g{}_g1'.format(G):
            ax1.plot(g_ret.index, logRet[col], 'r', label=col, alpha=1,
                     linewidth=1.5)
        elif col == 'zz500':
            ax1.plot(g_ret.index, logRet[col], 'b', label=col, alpha=1,
                     linewidth=1.5)
        else:
            ax1.plot(g_ret.index, logRet[col], label=col, alpha=0.8,
                     linewidth=0.5)
    #TODO: add relative return
    # ax1.plot(g_ret.index,logRet['g1']-logRet['zz500'])
    ax1.set_title('logRet')
    ax1.legend()

    ax2 = plt.subplot(223)
    ax2.bar(g_ret.index, g_ret['g10_g1'].values, width=20, alpha=1,color='b')
    ax2.set_xlabel('month_end')
    ax2.set_ylabel('return bar', color='b')
    [tl.set_color('b') for tl in ax2.get_yticklabels()]
    ax2.set_title('top minus bottom')

    ax3 = ax2.twinx()
    ax3.plot(g_ret.index, g_ret['g{}_g1'.format(G)].cumsum(), 'r-')
    ax3.set_ylabel('cumsum', color='r')
    [tl.set_color('r') for tl in ax3.get_yticklabels()]

    ax4 = plt.subplot(222)
    barlist = ax4.bar(range(g_ret_des['annual'].shape[0]), g_ret_des['annual'],
                      tick_label=g_ret_des.index, color='b')
    barlist[list(g_ret_des.index).index('g{}_g1'.format(G))].set_color('r')
    ax4.set_title('annual return')

    ax5=plt.subplot(224)
    ax5.stackplot(cover_rate.index,cover_rate.T.values,alpha=0.7)
    ax5.set_yticks(np.arange(0,1.2,step=0.2))
    ax5.set_title('cover rate')
    plt.close()#TODO: add grid
    #TODO： add title
    return fig

def filter_st_and_young_old(df, fdmt):
    data=pd.merge(fdmt.reset_index(),df.reset_index(),on=['stkcd','trd_dt'],how='left')
    data = data[(~data['type_st']) & (~ data['young_1year'])]  # 剔除st 和上市不满一年的数据
    data = data.groupby('stkcd').ffill(limit=FORWARD_TRADING_DAY) # debug: 向前填充最最多400个交易日,年度频率的数据，400 问题不大，但是对于月频的数据，最多向前填充400个交易日肯定是有问题的
    return data


def daily2monthly(daily):
    monthly=daily.groupby('stkcd').resample('M',on='trd_dt').last().dropna()
    del monthly['trd_dt']
    monthly.index.names=['stkcd','month_end']
    return monthly

def get_result(df,ret_1m,fdmt,zz500_ret_1m):
    '''
    df: pd.DataFrame,with only one column,and the index is ['stkcd','trd_dt']
    Args:
        df:
        ret_1m: stock return of the next month
        fdmt:
        zz500_ret_1m: zz500's return of the next month

    Returns:

    '''
    #review: 最后测试使用的月频数据，我们可以把计算的因子全部统一到月频上来，并且计算因子时候就ffill.用resample，所以把
    #review: date 全部变为 month_end. 包括trading_m等，只要是月频的全部变为month_end,Q全部变为quarter_end
    #review：这种情况下ffill也好控制，
    col=df.columns[0]
    monthly=filter_st_and_young(df, fdmt)
    cover_rate=get_cover_rate(monthly,col)

    #resample monthly to ease the calculation,but remember that resample will convert the trading date to calendar date(month end).
    monthly=monthly.dropna()
    monthly=monthly.groupby('month_end').filter(lambda x:x.shape[0]>300) #trick: filter,因为后边要进行行业中性化，太少的样本会出问题
    if monthly.shape[0]==0:
        print('The sample is too small!')
        return

    monthly=clean(monthly, col) # outlier,z_score,nutrualize

    #cross sectional analyse and layers test
    comb=pd.concat([ret_1m,monthly[col]],axis=1,join='inner').dropna()
    comb=comb.groupby('month_end').filter(lambda x:x.shape[0]>=50)#Trick:后边要进行分组分析，数据样本太少的话没法做

    if comb.shape[0]==0:
        print('The sample is too small!')
        return

    # cross section    beta tvalue ic
    beta_t_ic=comb.groupby('month_end').apply(get_beta_t_ic,col,'ret_1m')

    #layer test
    comb['g']=comb.groupby('month_end',group_keys=False).apply(
        lambda x:pd.qcut(x[col],G,labels=['g{}'.format(i) for i in range(1,G+1)]))
    g_ret=comb.groupby(['month_end','g'])['ret_1m'].mean().unstack('g')
    g_ret.columns=g_ret.columns.tolist()
    g_ret['g{}_g1'.format(G)]=g_ret['g{}'.format(G)]-g_ret['g1']#top minus bottom
    g_ret['zz500']=zz500_ret_1m
    g_ret=g_ret.dropna()
    return beta_t_ic,g_ret,cover_rate

fdmt_m = read_local('fdmt_m')[
    ['cap', 'type_st', 'wind_indcd', 'young_1year']]
ret_1m = read_local('trading_m')['ret_1m']
zz500_ret_1m=read_local('indice_m')['zz500_ret_1m']


def daily_to_monthly(df):
    monthly=df.resample('M').last()
    monthly.index.name='month_end'
    return monthly

def check_factor(df):
    '''
    Args:
        df: pd.DataFrame,with only one column,and the index is ['stkcd','trd_dt']

    Returns:

    '''
    beta_t_ic,g_ret,cover_rate=get_result(df, ret_1m, fdmt_m, zz500_ret_1m)

    beta_t_ic_des=beta_t_ic_describe(beta_t_ic)
    fig_beta_t_ic=plot_beta_t_ic(beta_t_ic)

    g_ret_des=g_ret_describe(g_ret)
    fig_g=plot_layer_analysis(g_ret, g_ret_des,cover_rate)

    dfs={'beta_t_ic':beta_t_ic,
       'beta_t_ic_des':beta_t_ic_des,
       'g_ret':g_ret,
       'g_ret_des':g_ret_des
       }
    figs={'fig_beta_t_ic':fig_beta_t_ic,
          'fig_g':fig_g}
    return dfs,figs

def save_results(dfs,figs,name):
    directory=os.path.join(SINGLE_D_CHECK,name)
    if not os.path.exists(directory):
        os.makedirs(directory)

    for k in dfs.keys():
        dfs[k].to_csv(os.path.join(directory, k + '.csv'))

    for k in figs.keys():
        figs[k].savefig(os.path.join(directory, k + '.png'))


def check_fn(fn):
    try:
        print(fn)
        path = os.path.join(SINGLE_D_INDICATOR, fn)
        df = pd.read_pickle(path)
        monthly = daily_to_monthly(df)
        monthly = monthly.stack().to_frame().swaplevel().sort_index()
        monthly.index.names = ['stkcd', 'month_end']
        monthly.columns = [fn[:-4]]
        dfs,figs=check_factor(monthly)
        save_results(dfs,figs,fn[:-4])
    except:
        print('{}------> wrong'.format(fn))
        pass

def main():
    fns=os.listdir(SINGLE_D_INDICATOR)
    fns=[fn for fn in fns if fn.endswith('.pkl')]
    checked=os.listdir(SINGLE_D_CHECK)
    fns = [fn for fn in fns if fn[:-4] not in checked]

    pool = multiprocessing.Pool(2)
    pool.map(check_fn, fns)

def debug():
    fn='C__est_bookvalue_FT24M_to_close_g_20.pkl'
    path = os.path.join(SINGLE_D_INDICATOR, fn)
    df = pd.read_pickle(path)
    monthly = daily_to_monthly(df)
    monthly = monthly.stack().to_frame().swaplevel()
    monthly.index.names=['stkcd','month_end']
    monthly=monthly.sort_index()
    monthly.columns = [fn[:-4]]
    dfs, figs=check_factor(monthly)
    save_results(dfs,figs,fn[:-4])

DEBUG=1

if __name__ == '__main__':
    if DEBUG:
        debug()
    else:
        main()

#TODO: adjust the spraed figure  and add title by using factor name





