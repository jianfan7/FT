# -*-coding: utf-8 -*-
# Python 3.6
# Author:Zhang Haitao
# Email:13163385579@163.com
# TIME:2018-07-09  09:08
# NAME:FT-read_data_base.py

# prerun section
import numpy as np
import pandas as pd
import pickle
import itertools
import os
import sys

from config import DIR_BACKTEST


sys.path.append('./lib')

import backtest.database_api as dbi
from sqlalchemy import create_engine
filesync_engine = create_engine('mysql+pymysql://ftresearch:FTResearch@192.168.1.140/filesync?charset=utf8')

start_date = '2005-01-01'
end_date = '2018-12-31'

stk_univ = slice(None)
backtest_data = os.path.join(DIR_BACKTEST,'backtest_data.h5')
signal_input_data = os.path.join(DIR_BACKTEST,'signal_input_data.h5')



# get backtest data

def get_zz500(start_date, end_date):
    zz500 = dbi.get_index_data('zz500', start_date, end_date)['zz500']
    zz500.index.name = 'trade_date'
    zz500.name = 'zz500'
    return zz500


def get_backtest_stocks_trade_data(start_date, end_date):
    stocks_trade_data = dbi.get_stocks_data(
        'equity_selected_trading_data',
        ['open', 'close', 'avgprice', 'adjfactor'],
        start_date, end_date)
    stocks_trade_data.columns = ['open', 'close', 'vwap', 'adj_factor']

    stocks_trade_data['open_post'] = stocks_trade_data['open'] * \
                                     stocks_trade_data['adj_factor']
    stocks_trade_data['close_post'] = stocks_trade_data['close'] * \
                                      stocks_trade_data['adj_factor']
    stocks_trade_data['vwap_post'] = stocks_trade_data['vwap'] * \
                                     stocks_trade_data['adj_factor']
    stocks_trade_data.index.names = ['trade_date', 'stock_ID']
    return stocks_trade_data


def get_stocks_trade_status(start_date, end_date):
    stocks_trade_status = \
    dbi.get_stocks_data('equity_selected_trading_data', ['tradestatus'],
                        start_date, end_date)['tradestatus']
    stocks_trade_status[stocks_trade_status != '停牌'] = 1
    stocks_trade_status[stocks_trade_status == '停牌'] = 0
    stocks_trade_status = stocks_trade_status.astype('float')
    stocks_trade_status.index.names = ['trade_date', 'stock_ID']
    return stocks_trade_status


def get_stocks_is_ST(start_date, end_date):
    stocks_is_ST = dbi.get_stocks_data('equity_fundamental_info', ['type_st'],
                                       start_date, end_date)['type_st']
    stocks_is_ST.index.names = ['trade_date', 'stock_ID']
    stocks_is_ST = stocks_is_ST.dropna()
    stocks_is_ST = pd.Series(stocks_is_ST.index.get_level_values(1),
                             index=pd.Index(
                                 stocks_is_ST.index.get_level_values(0),
                                 name='trade_date'))
    return stocks_is_ST.sort_index()


def get_stocks_ready_delist(start_date, end_date, ready_delist_days):
    stocks_delist_query = '''
    SELECT S_INFO_WINDCODE, S_INFO_LISTDATE
    FROM asharedescription
    WHERE S_INFO_DELISTDATE IS NOT NULL
    ORDER BY S_INFO_DELISTDATE DESC'''
    stocks_delist_date = pd.read_sql_query(stocks_delist_query,
                                           con=filesync_engine)

    stocks_delist_date.columns = ['stock_ID', 'delisted_date']
    stocks_delist_date['delisted_date'] = pd.to_datetime(
        stocks_delist_date['delisted_date'])

    ready_delist_stks = []
    for i in stocks_delist_date.index:
        stk = stocks_delist_date.loc[i, 'stock_ID']
        delist_date = stocks_delist_date.loc[i, 'delisted_date']
        ready_delist_date = pd.date_range(end=delist_date,
                                          periods=ready_delist_days, freq='B')
        ready_delist_stks.append(pd.Series(stk, index=ready_delist_date))
    ready_delist_stks = pd.concat(ready_delist_stks)

    ready_delist_stks.index.name = 'trade_date'
    return ready_delist_stks[start_date: end_date].sort_index()


def get_stocks_sub_new(start_date, end_date, sub_new_days):
    start_date_ = pd.to_datetime(start_date) - pd.offsets.BDay(sub_new_days)
    start_date_ = start_date_.strftime('%Y%m%d')
    end_date_ = ''.join(end_date.split('-'))

    stocks_sub_new_query = '''
    SELECT S_INFO_WINDCODE, S_INFO_LISTDATE
    FROM asharedescription
    WHERE S_INFO_LISTDATE>'{0}' AND S_INFO_LISTDATE<='{1}'
    ORDER BY S_INFO_LISTDATE DESC'''.format(start_date_, end_date_)
    stocks_sub_new = pd.read_sql_query(stocks_sub_new_query,
                                       con=filesync_engine)
    stocks_sub_new.columns = ['stock_ID', 'list_date']
    stocks_sub_new['list_date'] = pd.to_datetime(stocks_sub_new['list_date'])

    sub_new_stks = []
    for i in stocks_sub_new.index:
        stk = stocks_sub_new.loc[i, 'stock_ID']
        list_date = stocks_sub_new.loc[i, 'list_date']
        sub_new_date = pd.date_range(start=list_date, periods=sub_new_days,
                                     freq='B')
        sub_new_stks.append(pd.Series(stk, index=sub_new_date))
    sub_new_stks = pd.concat(sub_new_stks)

    sub_new_stks.index.name = 'trade_date'
    return sub_new_stks[start_date: end_date].sort_index()


zz500 = get_zz500(start_date, end_date)
stocks_trade_data = get_backtest_stocks_trade_data(start_date, end_date)
stocks_trade_status = get_stocks_trade_status(start_date, end_date)
stocks_is_ST = get_stocks_is_ST(start_date, end_date)
stocks_ready_delist = get_stocks_ready_delist(start_date, end_date, 10)
stocks_sub_new = get_stocks_sub_new(start_date, end_date, 260)

unpack = lambda x: stocks_trade_data[x].unstack().loc[:, stk_univ]
close_price_none = unpack('close')
close_price_post = unpack('close_post')
open_price_post = unpack('open_post')
vwap_post = unpack('vwap_post')

stocks_opened = stocks_trade_status.unstack().loc[:, stk_univ]

# stocks_need_drop = pd.concat([stocks_is_ST, stocks_ready_delist, stocks_sub_new])
# stocks_need_drop.sort_index(inplace=True)
stocks_need_drop = stocks_ready_delist

# update data into HDF file
data_names = (['zz500'] +
              ['close_price_none', 'close_price_post',
               'open_price_post', 'vwap_post'] +
              ['stocks_opened', 'stocks_need_drop'])

with pd.HDFStore(backtest_data) as file:
    for n in data_names:
        file.put(n, eval(n), format='t', append=True)
    print(file)

# get sinal input data

def get_stocks_trade_data(start_date, end_date):
    stocks_trade_data = dbi.get_stocks_data(
        'equity_selected_trading_data',
        ['close', 'adjfactor'],
        start_date, end_date)
    stocks_trade_data.columns = ['close', 'adj_factor']
    stocks_trade_data['close_post'] = (stocks_trade_data['close'] *
                                       stocks_trade_data['adj_factor'])
    stocks_trade_data.index.names = ['trade_date', 'stock_ID']
    return stocks_trade_data


# def get_stocks_trade_status(start_date, end_date):
#     stocks_trade_status = dbi.get_stocks_data('equity_selected_trading_data', ['tradestatus'],
#                                               start_date, end_date)['tradestatus']
#     stocks_trade_status[stocks_trade_status != '停牌'] = 1
#     stocks_trade_status[stocks_trade_status == '停牌'] = 0
#     stocks_trade_status = stocks_trade_status.astype('float')
#     stocks_trade_status.index.names = ['trade_date', 'stock_ID']
#     return stocks_trade_status


def get_stocks_industry_L4(start_date, end_date):
    stocks_industry_L4 = dbi.get_stocks_data('equity_fundamental_info', ['wind_indcd'],
                                             start_date, end_date)['wind_indcd']
    stocks_industry_L4 -= 6200000000
    stocks_industry_L4.index.names = ['trade_date', 'stock_ID']
    stocks_industry_L4 = stocks_industry_L4.unstack()
    return stocks_industry_L4


stocks_trade_data = get_stocks_trade_data(start_date, end_date)
stocks_trade_status = get_stocks_trade_status(start_date, end_date)
stocks_industry_L4 = get_stocks_industry_L4(start_date, end_date)

stocks_trade_data[stocks_trade_status == 0] = np.nan
close_price_post = stocks_trade_data['close_post'].unstack().loc[:, stk_univ]

stocks_industry_L4 = stocks_industry_L4.loc[:, stk_univ]

# update data to HDF file
data_names = ['close_price_post', 'stocks_industry_L4']
with pd.HDFStore(signal_input_data) as file:
    for n in data_names:
        file.put(n, eval(n), format='t', append=True)
    print(file)
