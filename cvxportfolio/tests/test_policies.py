# Copyright 2023- The Cvxportfolio Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

from pathlib import Path

import cvxpy as cvx
import numpy as np
import pandas as pd

from cvxportfolio.policies import *
# from cvxportfolio.policies import SinglePeriodOptOLD, SinglePeriodOptNEW
from cvxportfolio.returns import *
from cvxportfolio.risks import *
from cvxportfolio.costs import *
from cvxportfolio.constraints import *
from cvxportfolio.errors import *


class TestPolicies(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Load the data and initialize cvxpy vars."""
        # cls.sigma = pd.read_csv(Path(__file__).parent / "sigmas.csv", index_col=0, parse_dates=[0])
        cls.returns = pd.read_csv(Path(__file__).parent / "returns.csv", index_col=0, parse_dates=[0])
        cls.volumes = pd.read_csv(Path(__file__).parent / "volumes.csv", index_col=0, parse_dates=[0])
        cls.w_plus = cvx.Variable(cls.returns.shape[1])
        cls.w_plus_minus_w_bm = cvx.Variable(cls.returns.shape[1])
        cls.z = cvx.Variable(cls.returns.shape[1])
        cls.N = cls.returns.shape[1]

    def test_hold(self):
        hold = Hold()
        w = pd.Series(0.5, ["AAPL", "CASH"])
        self.assertTrue(np.all(
            hold.values_in_time(current_weights=w).values == np.zeros(2)))
            
            
    def test_rank_and_long_short(self):
        hold = Hold()
        w = pd.Series(0.25, ["AAPL", "TSLA", "GOOGL", "CASH"])
        signal = pd.Series([1, 2, 3], ["AAPL", "TSLA", "GOOGL"])
        num_long = 1
        num_short = 1
        target_leverage = 3.0
        rls = RankAndLongShort(
            signal=signal,
            num_long=num_long,
            num_short=num_short,
            target_leverage=target_leverage,
        )
        z = rls.values_in_time(t=None, current_weights=w)
        print(z)
        wplus = w + z
        self.assertTrue(wplus["CASH"] == 1)
        self.assertTrue( wplus["TSLA"] == 0)
        self.assertTrue( wplus["AAPL"] == -wplus["GOOGL"])
        self.assertTrue( np.abs(wplus[:-1]).sum() == 3)

        index = pd.date_range("2020-01-01", "2020-01-03")
        signal = pd.DataFrame(
            {
                "AAPL": pd.Series([1, 1.9, 3], index),
                "TSLA": pd.Series([3, 2.1, 1], index),
                "GOOGL": pd.Series([4, 4, 4], index),
            }
        )
        rls = RankAndLongShort(
            signal=signal,
            num_long=num_long,
            num_short=num_short,
            target_leverage=target_leverage,
        )
        z1 = rls.values_in_time(t=index[0], current_weights=w)
        print(z1)
        wplus = w + z1
        self.assertTrue( wplus["CASH"] == 1)
        self.assertTrue( wplus["TSLA"] == 0)
        self.assertTrue( wplus["AAPL"] == -wplus["GOOGL"])
        self.assertTrue( np.abs(wplus[:-1]).sum() == 3)
        z2 = rls.values_in_time(t=index[1], current_weights=w)
        print(z2)
        wplus = w + z2
        self.assertTrue( wplus["CASH"] == 1)
        self.assertTrue( wplus["TSLA"] == 0)
        self.assertTrue( wplus["AAPL"] == -wplus["GOOGL"])
        self.assertTrue( np.abs(wplus[:-1]).sum() == 3)
        z3 = rls.values_in_time(t=index[2], current_weights=w)
        wplus = w + z3
        self.assertTrue( wplus["CASH"] == 1)
        self.assertTrue( wplus["AAPL"] == 0)
        self.assertTrue( wplus["TSLA"] == -wplus["GOOGL"])
        self.assertTrue( np.abs(wplus[:-1]).sum() == 3)
        print(z3)


    def test_proportional_trade(self):
    
        a = pd.Series(1., self.returns.columns)
        a[-1] = 1 - sum(a[:-1])
        b = pd.Series(-1., self.returns.columns)
        b[-1] = 1 - sum(b[:-1])

        targets = pd.DataFrame({self.returns.index[3]: a,
                                self.returns.index[15]: b
                                }).T
        policy = ProportionalTradeToTargets(targets)

        policy.pre_evaluation(universe=self.returns.columns, backtest_times=self.returns.index)
        start_portfolio = pd.Series(
            np.random.randn(
                self.returns.shape[1]),
            self.returns.columns)
        start_portfolio[-1] = 1 - sum(start_portfolio[:-1])
        for t in self.returns.index[:17]:
            print(t)
            print(start_portfolio)
        
            trade = policy.values_in_time(t=t, current_weights=start_portfolio)
            start_portfolio += trade
        
            if t in targets.index:
                self.assertTrue(np.all(start_portfolio == targets.loc[t]))

        self.assertTrue( np.all(trade == 0.))
        
    def test_sell_all(self):
        start_portfolio = pd.Series(
            np.random.randn(
                self.returns.shape[1]),
            self.returns.columns)
        policy = SellAll()
        t = pd.Timestamp('2022-01-01')
        trade = policy.values_in_time(t=t, current_weights=start_portfolio)
        allcash = np.zeros(len(start_portfolio))
        allcash[-1] = 1
        assert isinstance(trade, pd.Series)
        assert np.allclose(allcash, start_portfolio + trade)


    def test_fixed_trade(self):
        fixed_trades = pd.DataFrame(
            np.random.randn(
                len(self.returns),
                self.returns.shape[1]),
            index=self.returns.index,
            columns=self.returns.columns)

        policy = FixedTrades(fixed_trades)
        t = self.returns.index[123]
        trade = policy.values_in_time(t=t, current_weights=pd.Series(
            0., self.returns.columns))
        self.assertTrue(np.all(trade == fixed_trades.loc[t]))

        t = pd.Timestamp('1900-01-01')
        trade = policy.values_in_time(t=t, current_weights=trade)
        self.assertTrue(np.all(trade == 0.))


    def test_fixed_weights(self):
        fixed_weights = pd.DataFrame(
            np.random.randn(
                len(self.returns),
                self.returns.shape[1]),
            index=self.returns.index,
            columns=self.returns.columns)

        policy = FixedWeights(fixed_weights)
        t = self.returns.index[123]
        trade = policy.values_in_time(t=t, current_weights=pd.Series(
            0., self.returns.columns))
        self.assertTrue(np.all(trade == fixed_weights.loc[t]))

        t = self.returns.index[111]
        trade = policy.values_in_time(t=t, current_weights=fixed_weights.iloc[110])
        self.assertTrue( np.allclose(trade + fixed_weights.iloc[110], fixed_weights.loc[t]))

        t = pd.Timestamp('1900-01-01')
        trade = policy.values_in_time(t=t, current_weights=trade)
        self.assertTrue( np.all(trade == 0.))


    def test_periodic_rebalance(self):

        target = pd.Series(np.random.uniform(size=self.returns.shape[1]), self.returns.columns)
        target /= sum(target)
        rebalancing_times = pd.date_range(start=self.returns.index[0], end=self.returns.index[-1], 
            freq='7d')

        policy = PeriodicRebalance(target, rebalancing_times=rebalancing_times)
        init = pd.Series(np.random.randn(self.returns.shape[1]), self.returns.columns)

        trade = policy.values_in_time(t=rebalancing_times[0], current_weights=init)
        self.assertTrue(np.allclose(trade + init, target))

        trade = policy.values_in_time(t=rebalancing_times[0] + pd.Timedelta('1d'),
            current_weights=init)
        self.assertTrue(np.allclose(trade, 0))

    def test_uniform(self):
        pol = Uniform()
        pol.pre_evaluation(self.returns.columns, self.returns.index)
        
        init = pd.Series(np.random.randn(self.returns.shape[1]), self.returns.columns)
        trade = pol.values_in_time(t=self.returns.index[123], current_weights=init)
        self.assertTrue(np.allclose((trade + init)[:-1], 
            np.ones(self.returns.shape[1]-1)/(self.returns.shape[1]-1)))
        

    def test_proportional_rebalance(self):

        target = pd.Series(np.random.uniform(size=self.returns.shape[1]), self.returns.columns)
        target /= sum(target)
        target_matching_times = self.returns.index[::3]

        policy = ProportionalRebalance(target, target_matching_times=target_matching_times)
        policy.pre_evaluation(universe=self.returns.columns, backtest_times=self.returns.index)

        init = pd.Series(np.random.randn(self.returns.shape[1]), self.returns.columns)

        trade = policy.values_in_time(t=self.returns.index[1], current_weights=init)
        init += trade
        trade2 = policy.values_in_time(t=self.returns.index[2], current_weights=init)
        self.assertTrue(np.allclose(trade, trade2))
        self.assertTrue(np.allclose(trade + trade2 + init, target))
    
    def test_adaptive_rebalance(self):
        np.random.seed(0)
        target = pd.Series(
            np.random.uniform(
                size=self.returns.shape[1]),
            self.returns.columns)
        target /= sum(target)
        target = pd.DataFrame({ind: target for ind in self.returns.index}).T

        init = pd.Series(np.random.uniform(size=self.returns.shape[1]), self.returns.columns)
        init /= sum(init)

        for tracking_error in [0.01, .02, .05, .1]:
            policy = AdaptiveRebalance(target, tracking_error=tracking_error)
            trade = policy.values_in_time(t=self.returns.index[1], current_weights=init)
            self.assertTrue(np.allclose(init + trade, target.iloc[0]))

        for tracking_error in [.2, .5]:
            policy = AdaptiveRebalance(target, tracking_error=tracking_error)
            trade = policy.values_in_time(t=self.returns.index[1], current_weights=init)
            self.assertTrue(np.allclose(trade, 0.))


    def test_single_period_optimization(self):

        return_forecast = ReturnsForecast(lastforcash=False)
        risk_forecast = FullCovariance(addmean=False)
        tcost = TransactionCost(spreads=1E-3, pershare_cost=0., b=0., exponent=2)
        
        
        policy = SinglePeriodOptimization(
            return_forecast
            - 2 * risk_forecast
            -tcost
            #- TcostModel(half_spread=5 * 1E-4)  # , power=2)
            ,
            constraints=[LongOnly(), LeverageLimit(1)],
            # verbose=True,
            solver='ECOS')
            

        policy.pre_evaluation(universe=self.returns.columns, backtest_times=self.returns.index)

        
        curw = np.zeros(self.N)
        curw[-1] = 1.

        result = policy.values_in_time(
            t=self.returns.index[121],
            current_weights=pd.Series(
                curw,
                self.returns.columns),
            current_portfolio_value=1000,
            past_returns=self.returns.iloc[:121],
            past_volumes=self.volumes.iloc[:121],
            current_prices=pd.Series(1., self.volumes.columns))
            
       

        cvxportfolio_result = pd.Series(result, self.returns.columns)

        print(cvxportfolio_result)
        
        # print(np.linalg.eigh(self.returns.iloc[:121, :-1].cov().values)[0])

        # REPLICATE WITH CVXPY
        w = cvx.Variable(self.N)
        cvx.Problem(cvx.Maximize(w.T @ self.returns.iloc[:121].mean().values -
                                 2 * cvx.quad_form(w[:-1], self.returns.iloc[:121, :-1].cov(ddof=0).values) -
                                 5 * 1E-4 * cvx.sum(cvx.abs(w - curw)[:-1])
                                 ),
                    [w >= 0, w <= 1, sum(w) == 1]
                    ).solve(solver='ECOS')

        cvxpy_result = pd.Series(w.value - curw, self.returns.columns)

        print(cvxpy_result)
        
        print(cvxportfolio_result - cvxpy_result)
        self.assertTrue(np.allclose(cvxportfolio_result - cvxpy_result, 0., atol=1e-5))
    
    
    
    def test_single_period_optimization_solve_twice(self):

        return_forecast = ReturnsForecast()
        risk_forecast = FullCovariance()
        
        policy = SinglePeriodOptimization(
            return_forecast
            - 2 * risk_forecast
            - TransactionCost(spreads=10 * 1E-4, pershare_cost=0., b=0.)  # , power=2)
            ,
            constraints=[LongOnly(), LeverageLimit(1)],
            # verbose=True,
            solver='ECOS')

        policy.pre_evaluation(universe=self.returns.columns, backtest_times=self.returns.index)

        curw = np.zeros(self.N)
        curw[-1] = 1.

        result = policy.values_in_time(
            t=self.returns.index[134],
            current_weights=pd.Series(
                curw,
                self.returns.columns),
            current_portfolio_value=1000,
            past_returns=self.returns.iloc[:134],
            past_volumes=self.volumes.iloc[:134],
            current_prices=pd.Series(1., self.volumes.columns))

        self.assertFalse(np.allclose(result, 0.))

        cvxportfolio_result = pd.Series(result, self.returns.columns)

        curw += result

        result2 = policy.values_in_time(
            t=self.returns.index[134],
            current_weights=pd.Series(
                curw,
                self.returns.columns),
            current_portfolio_value=1000,
            past_returns=self.returns.iloc[:134],
            past_volumes=self.volumes.iloc[:134],
            current_prices=pd.Series(1., self.volumes.columns))

        self.assertTrue(np.allclose(result2, 0., atol=1e-7))
        
        
    def test_single_period_optimization_infeasible(self):

        return_forecast = ReturnsForecast()
        risk_forecast = FullCovariance()
        policy = SinglePeriodOptimization(
            return_forecast
            - 2 * risk_forecast
            - TransactionCost(spreads=10 * 1E-4, pershare_cost=0., b=0.)  # , power=2)
            ,
            constraints=[LongOnly(), LeverageLimit(1), MaxWeights(-1)],
            # verbose=True,
            solver='ECOS')

        policy.pre_evaluation(universe=self.returns.columns, backtest_times=self.returns.index)


        curw = np.zeros(self.N)
        curw[-1] = 1.

        with self.assertRaises(PortfolioOptimizationError):
            result = policy.values_in_time(
                t=self.returns.index[134],
                current_weights=pd.Series(
                    curw,
                    self.returns.columns),
                current_portfolio_value=1000,
                past_returns=self.returns.iloc[:134],
                past_volumes=self.volumes.iloc[:134],
                current_prices=pd.Series(1., self.volumes.columns))
            
    def test_single_period_optimization_unbounded(self):

        return_forecast = ReturnsForecast()
        risk_forecast = FullCovariance()
        policy = SinglePeriodOptimization(
            return_forecast
            #- 2 * risk_forecast
            #- TransactionCost(spreads=10 * 1E-4, pershare_cost=0., b=0.)  # , power=2)
            ,
            constraints=[LongOnly(), #LeverageLimit(1), MaxWeights(-1)
        ],
            # verbose=True,
            solver='ECOS')

        policy.pre_evaluation(universe=self.returns.columns, backtest_times=self.returns.index)


        curw = np.zeros(self.N)
        curw[-1] = 1.

        with self.assertRaises(PortfolioOptimizationError):
            result = policy.values_in_time(
                t=self.returns.index[134],
                current_weights=pd.Series(
                    curw,
                    self.returns.columns),
                current_portfolio_value=1000,
                past_returns=self.returns.iloc[:134],
                past_volumes=self.volumes.iloc[:134],
                current_prices=pd.Series(1., self.volumes.columns))
     
    def test_multi_period_optimization2(self):
        """Test that MPO1 and MPO2 and MPO5 return same if no tcost, and diff if tcost"""

        results = []
        for planning_horizon in [1,2,5]:
            return_forecast = ReturnsForecast()
            risk_forecast = FullCovariance()
            policy = MultiPeriodOptimization(
                return_forecast
                - 10 * risk_forecast
                #- TcostModel(half_spread=5 * 1E-4)  # , power=2)
                ,
                constraints=[LongOnly(), LeverageLimit(1)],
                # verbose=True,
                planning_horizon=planning_horizon,
                solver='ECOS')

            policy.pre_evaluation(universe=self.returns.columns, backtest_times=self.returns.index)


            curw = np.zeros(self.N)
            curw[-1] = 1.

            results.append(policy.values_in_time(
                t=self.returns.index[67],
                current_weights=pd.Series(
                    curw,
                    self.returns.columns),
                current_portfolio_value=1000,
                past_returns=self.returns.iloc[:67],
                past_volumes=self.volumes.iloc[:67],
                current_prices=pd.Series(1., self.volumes.columns)))

        self.assertTrue(np.allclose(results[0], results[1], atol=1e-4))
        self.assertTrue(np.allclose(results[1], results[2], atol=1e-4))

        # with tcost

        results = []
        for planning_horizon in [1,2,5]:
            return_forecast = ReturnsForecast()
            risk_forecast = FullCovariance()
            policy = MultiPeriodOptimization(
                return_forecast
                - 10 * risk_forecast
                - TransactionCost(spreads=50 * 1E-4, pershare_cost=0., b=0.)
                #- TcostModel(half_spread=5 * 1E-4)  # , power=2)
                ,
                constraints=[LongOnly(), LeverageLimit(1)],
                # verbose=True,
                planning_horizon=planning_horizon,
                solver='ECOS')

            policy.pre_evaluation(universe=self.returns.columns, backtest_times=self.returns.index)

            curw = np.zeros(self.N)
            curw[-1] = 1.

            results.append(policy.values_in_time(
                t=self.returns.index[67],
                current_weights=pd.Series(
                    curw,
                    self.returns.columns),
                current_portfolio_value=1000,
                past_returns=self.returns.iloc[:67],
                past_volumes=self.volumes.iloc[:67],
                current_prices=pd.Series(1., self.volumes.columns)))

        self.assertFalse(np.allclose(results[0], results[1], atol=1e-4))
        self.assertFalse(np.allclose(results[1], results[2], atol=1e-4))
        
    def test_multi_period_optimization_syntax(self):
        with self.assertRaises(SyntaxError):
            MultiPeriodOptimization([ReturnsForecast()], [])
        with self.assertRaises(SyntaxError):
            MultiPeriodOptimization([ReturnsForecast()], [[],[]])
        with self.assertRaises(SyntaxError):
            MultiPeriodOptimization([ReturnsForecast()], None)
        with self.assertRaises(SyntaxError):
            MultiPeriodOptimization(ReturnsForecast())
        MultiPeriodOptimization(ReturnsForecast(), planning_horizon = 1)
        
    def test_multi_period_optimization3(self):
        """Check that terminal constraint brings closer to benchmark."""
    
        np.random.seed(0)
        benchmark = np.random.uniform(size=self.returns.shape[1])
        benchmark /= sum(benchmark)
        benchmark = pd.Series(benchmark, self.returns.columns)
    
        diff_to_benchmarks = []
        for planning_horizon in [1,2,5]:

            return_forecast = ReturnsForecast()
            risk_forecast = FullCovariance()
            policy = MultiPeriodOptimization(
                return_forecast
                - 10 * risk_forecast
                - TransactionCost(spreads=10 * 1E-4, pershare_cost=0., b=0.)  # , power=2)
                ,
                constraints=[LongOnly(), LeverageLimit(1)],
                #verbose=True,
                terminal_constraint=benchmark,
                planning_horizon=planning_horizon,
                solver='ECOS')

            policy.pre_evaluation(universe=self.returns.columns, backtest_times=self.returns.index)

            curw = np.zeros(self.N)
            curw[-1] = 1.

            diff_to_benchmarks.append(policy.values_in_time(
                t=self.returns.index[67],
                current_weights=pd.Series(
                    curw,
                    self.returns.columns),
                current_portfolio_value=1000,
                past_returns=self.returns.iloc[:67],
                past_volumes=self.volumes.iloc[:67],
                current_prices=pd.Series(1., self.volumes.columns)) + curw - benchmark)
                                        
        self.assertTrue(np.isclose(np.linalg.norm(diff_to_benchmarks[0]), 0.))
        self.assertTrue(np.linalg.norm(diff_to_benchmarks[0]) < np.linalg.norm(diff_to_benchmarks[1]))
        self.assertTrue(np.linalg.norm(diff_to_benchmarks[1]) < np.linalg.norm(diff_to_benchmarks[2]))
    
    
if __name__ == '__main__':
    unittest.main()
        


            


    
    
# def test_multi_period_optimization1(returns, volumes):
#     """Test that SPO and MPO1 return same"""
#     N = returns.shape[1]
#     return_forecast = ReturnsForecast(rolling=50)
#     risk_forecast = FullCovariance(rolling=50)
#     policy = MultiPeriodOptimization(
#         return_forecast
#         - 2 * risk_forecast
#         - TcostModel(half_spread=5 * 1E-4)  # , power=2)
#         ,
#         constraints=[LongOnly(), LeverageLimit(1)],
#         # verbose=True,
#         planning_horizon=1,
#         solver='ECOS')
#
#     policy.pre_evaluation(returns,
#                           volumes,
#                           start_time=returns.index[51],
#                           end_time=returns.index[-1])
#
#     curw = np.zeros(N)
#     curw[-1] = 1.
#
#     result = policy.values_in_time(
#         t=returns.index[51],
#         current_weights=pd.Series(
#             curw,
#             returns.columns),
#         current_portfolio_value=1000,
#         past_returns=None,
#         past_volumes=None)
#
#     cvxportfolio_result = pd.Series(result, returns.columns)
#
#     return_forecast = ReturnsForecast(rolling=50)
#     risk_forecast = FullCovariance(rolling=50)
#
#     policy1 = SinglePeriodOptimization(
#         return_forecast
#         - 2 * risk_forecast
#         - TcostModel(half_spread=5 * 1E-4)  # , power=2)
#         ,
#         constraints=[LongOnly(), LeverageLimit(1)],
#         # verbose=True,
#         solver='ECOS')
#
#     policy1.pre_evaluation(returns,
#                           volumes,
#                           start_time=returns.index[51],
#                           end_time=returns.index[-1])
#
#     result1 = policy1.values_in_time(
#         t=returns.index[51],
#         current_weights=pd.Series(
#             curw,
#             returns.columns),
#         current_portfolio_value=1000,
#         past_returns=None,
#         past_volumes=None)
#
#     cvxportfolio_result1 = pd.Series(result1, returns.columns)
#
#     assert np.allclose(cvxportfolio_result - cvxportfolio_result1, 0., atol=1e-7)
    

        

        
        
# def test_spo_old_vs_new(returns, volumes, sigma):
#     tcost_model = TcostModel(half_spread=0.0005, nonlin_coeff=1.0, volume=volumes, sigma=sigma,
#     )
#     #hcost_model = HcostModel(borrow_costs=0., dividends=0.)
#     emp_Sigma = np.cov(returns.iloc[:, :-1].to_numpy().T)
#     risk_model = FullCovariance(emp_Sigma)
#     returns_forecast = ReturnsForecast(returns.mean())
#
#     pol = SinglePeriodOptOLD(
#         returns_forecast, [
#             10 * risk_model,
#             2 * tcost_model,
#             #hcost_model
#         ], [], solver=cvx.ECOS)#, solver_opts={'verbose':True})#, solver_opts={'abstol':1E-16, 'reltol':1e-16, 'feastol':1e-16})
#
#     #np.random.seed(0)
#     init = pd.Series(1., index = returns.columns)
#     init *= 1E6
#
#     trad = pol.get_trades(init, t=returns.index[10])
#
#     print(trad)
#
#     # raise Exception
#
#     # print(pol.costs[1].costs[0].second_term_multiplier.value)
#     risk_model = FullCovariance(emp_Sigma)
#     returns_forecast = ReturnsForecast(returns.mean())
#     tcost_model = TcostModel(half_spread=0.0005, nonlin_coeff=1.0, volume=volumes, sigma=sigma,)
#     hcost_model = HcostModel(borrow_costs=0., dividends=0.)
#
#     pol_new = SinglePeriodOptNEW(
#         returns_forecast, [
#             10 * risk_model,
#             2 * tcost_model,
#             #hcost_model
#         ], [], solver=cvx.ECOS)#, solver_opts={'verbose':True})#, solver_opts={'abstol':1E-16, 'reltol':1e-16, 'feastol':1e-16})
#
#     trad_new = pol_new.get_trades(init, t=returns.index[10])
#
#     print(trad_new)
#
#     # print(pol_new.objective[0].costs[2].second_term_multiplier.value)
#
#     assert np.allclose(trad/1E6, trad_new/1E6, atol=1e-4)
#
#     ### CVXPY
#     w = cvx.Variable(returns.shape[1])
#     z = cvx.Variable(returns.shape[1])
#     w0 = init / sum(init)
#     mu = returns.mean()
#     Sigma = emp_Sigma
#     V = volumes.iloc[10]
#     val = sum(init)
#     s = sigma.iloc[10]
#     objective = cvx.Maximize(w.T @ mu
#         - 10 * cvx.quad_form(w[:-1], Sigma)
#             - 2 * 0.0005 * cvx.norm1(z[:-1])
#             - 2 * (cvx.abs(z[:-1])**1.5).T @ (s * np.sqrt(val / V))
#             )
#     cvx.Problem(objective, [cvx.sum(z) == 0, z + w0 == w]).solve(solver='ECOS')#, abstol=1E-16, reltol=1e-16, feastol=1e-16)
#
#     trad_cvxpy = pd.Series(val * w.value - init, returns.columns)
#     assert np.allclose((trad_cvxpy - trad_new)/sum(init), 0., atol=1E-3)    
    
    
    
        