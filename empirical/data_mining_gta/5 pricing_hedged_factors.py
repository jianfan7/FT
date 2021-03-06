# -*-coding: utf-8 -*-
# Python 3.6
# Author:Zhang Haitao
# Email:13163385579@163.com
# TIME:2018-09-15  19:29
# NAME:FT_hp-5 5 pricing_hedged_factors.py

from empirical.config_ep import DIR_DM_GTA
from empirical.data_mining_gta.dm_api import pricing_all_factors
from empirical.get_basedata import BENCHS, get_benchmark
import os
import pandas as pd

DIR_ANALYSE= os.path.join(DIR_DM_GTA, 'analyse')




def get_alpha_t_for_all_bm():
    for bname in BENCHS:
        print(bname)
        bench=get_benchmark(bname)
        # if isinstance(bench, pd.Series):#capmM
        #     bench = bench.to_frame()
        s=pricing_all_factors(bench)
        s.to_pickle(os.path.join(DIR_ANALYSE, f'at_{bname}.pkl'))#alpha t value

def combine_at():
    at = pd.concat(
        [pd.read_pickle(os.path.join(DIR_ANALYSE, f'at_{bench}.pkl'))
         for bench in BENCHS], axis=1,keys=BENCHS,sort=True)
    at.to_pickle(os.path.join(DIR_ANALYSE, 'at.pkl'))


def main():
    get_alpha_t_for_all_bm()
    combine_at()


if __name__ == '__main__':
    main()
