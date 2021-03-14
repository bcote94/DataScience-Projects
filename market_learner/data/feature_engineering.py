import numpy as np
import pandas as pd
from utils import logger
from utils.constants import *

LOGGER = logger.setup_logger(__name__)


class FeatureEngineering(object):

    def __init__(self, lookback, window, length):
        self.lookback = lookback
        self.window = window
        self.length = length

    def run(self, data):
        df = pd.DataFrame([], columns=MODEL_VARIABLES, index=data.index)

        df['slow_stochastic_%K'], df['fast_stochastic_%D'], df['williams_%R'] = self._stochastic_oscillators(data)
        df['price_difference'], df['price_ROC'] = self._momentum_oscillators(data)
        df['RSI'] = self._rsi(data)
        df['ATR'] = self._atr(data)
        df['average_price_volatility'], df['disparity_index'] = self._volatility(data)
        df['MACD'] = self._macd(data)
        df['on_balance_volume'], df['label'] = self._vol_label(data)
        return df

    def _stochastic_oscillators(self, data):
        kmat = np.zeros(self.length)
        dmat = np.zeros(self.length)
        rmat = np.zeros(self.length)

        # TODO: This will be tricky to vectorize since variable start-points, but take a look at it.
        # Theory-- Can slice the data and then run a function on the vectorized slice, if that's faster?
        for i in range(self.lookback, self.length):
            c = data.Close.iloc[i, ]
            low = min(data.Close.iloc[i - self.lookback:i, ])
            high = max(data.Close.iloc[i - self.lookback:i, ])
            kmat[i] = (c - low) / (high - low) * 100
            rmat[i] = (high - c) / (high - low) * -100

        for i in range(self.lookback, self.length):
            for j in (range(0, self.lookback - 1)):
                dmat[i] = dmat[i] + kmat[i - j] / self.lookback
        return kmat, dmat, rmat

    def _momentum_oscillators(self, data):
        mom = np.zeros(self.length)
        ROC = np.zeros(self.length)

        for i in range(self.lookback, self.length):
            mom[i] = data.Close.iloc[i, ] - data.Close.iloc[i - self.lookback, ]
            ROC[i] = (data.Close.iloc[i, ] - data.Close.iloc[i - self.lookback, ]) / data.Close.iloc[i - self.lookback, ]
        return mom, ROC

    def _rsi(self, data):
        rsi = np.zeros(self.length)
        change = np.zeros(self.length)
        gain = np.zeros(self.length)
        loss = np.zeros(self.length)
        avgGain = np.zeros(self.length)
        avgLoss = np.zeros(self.length)

        for i in range(1, self.length):
            change[i] = data.Close.iloc[i] - data.Close.iloc[i - 1, ]
            if change[i] > 0:
                gain[i] += change[i]
            else:
                loss[i] += abs(change[i])

        for i in range(self.lookback, self.length):
            local_gain = gain[i - self.lookback:i]
            local_loss = loss[i - self.lookback:i]
            avgGain[i] = sum(local_gain) / self.lookback
            avgLoss[i] = sum(local_loss) / self.lookback
            rs = avgGain[i] / avgLoss[i]
            rsi[i] = 100 - (100 / (1 + rs))
        return rsi

    def _atr(self, data):
        true_range = np.zeros(self.length)
        
        for i in range(1, self.length):
            x0 = data.High.iloc[i, ] - data.Low.iloc[i, ]
            x1 = abs(data.High.iloc[i, ] - data.Close.iloc[i - 1, ])
            x2 = abs(data.Low.iloc[i, ] - data.Close.iloc[i - 1, ])
            true_range[i] = max(x0, x1, x2)
        return list(pd.Series(true_range).ewm(span=14).mean())

    def _volatility(self, data):
        vol = np.zeros(self.length)
        dis = np.zeros(self.length)
        
        for i in range(self.lookback, self.length):
            c = 0
            dis[i] = 100 * data.Close.iloc[i, ] / data.Close.iloc[i - 10:i, ].mean()
            for j in range(i - self.lookback + 1, i):
                x1 = data.Close.iloc[j, ]
                x0 = data.Close.iloc[j - 1, ]
                c += (x1 - x0) / x0
            vol[i] = 100 * c / self.lookback
        return vol, dis

    def _macd(self, data):
        macd = np.zeros(self.length)
        exp12 = np.zeros(self.length)
        exp26 = np.zeros(self.length)

        exp12[0] = data.Close.iloc[0:11, ].mean()
        for i in range(1, self.length - 11):
            exp12[i] = (data.Close.iloc[11 + i, ] - exp12[i - 1]) * MULT12 + exp12[i - 1]

        # TODO: WTF is 25 and 11 here??? Surely you had a reason???
        exp26[0] = data.Close.iloc[0:25, ].mean()
        for i in range(1, self.length - 25):
            exp26[i] = (data.Close.iloc[25 + i, ] - exp26[i - 1]) * MULT26 + exp26[i - 1]
            macd[i] = exp12[i] - exp26[i]
        return macd

    def _vol_label(self, data):
        labels = np.zeros(self.length)
        obv = np.zeros(self.length)
        obv[0] = data.Volume.iloc[0]

        for i in range(1, self.length):
            change = data.Close.iloc[i - 1, ] - data.Close.iloc[i, ]

            if change > 0:
                obv[i] = obv[i - 1] + data.Volume.iloc[i, ]
            elif change < 0:
                obv[i] = obv[i - 1] - data.Volume.iloc[i, ]
            else:
                obv[i] = obv[i - 1]

        for i in range(1, self.length - self.window):
            if (data.Close.iloc[i + self.window, ] - data.Close.iloc[i, ]) >= 0:
                labels[i] = 1
            if (data.Close.iloc[i + self.window, ] - data.Close.iloc[i, ]) < 0:
                labels[i] = -1
        labels = [label if label == -1 else 1 for label in labels]
        return obv, labels
















