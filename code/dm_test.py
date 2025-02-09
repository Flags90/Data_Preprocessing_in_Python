# импорт необходимых библиотек
import numpy as np
from scipy.stats import t
from collections import namedtuple
from re import compile as re_compile
import statsmodels.api as sm


# класс, реализующий тест Диболда-Мариано для сравнения качества
# прогнозов временного ряда двух прогнозных моделей
# (1995), с модификацией, предложенной Харви и др.(1997)
class DieboldMarianoTest:
    """
    Параметры
    crit: строковое значение, определяющее критерий,
        может принимать следующие значения:
        MSE: среднеквадратическая ошибка
        MAE: средняя абсолютная ошибка 
        MAD: среднее абсолютное отклонение
        MAPE: средняя абсолютная процентная ошибка
        MASE: средняя абсолютная масштабированная ошибка
        MRAE: Средняя относительная абсолютная ошибка
        SMAPE: Симметричная средняя абсолютная процентная ошибка
        poly: использование степенной функции для взвешивания ошибок
        ALL: расчет по всем предыдущим критериям
    power: степень в функции для взвешивания ошибок
        (имеет смысл, только когда crit="poly")
    h: количество шагов вперед
    seasonal_period: количество периодов в полном сезонном цикле 
        (например, 4 - для квартальных данных, 7 - для ежедневных данных 
        с недельным циклом), используется только при расчете MASE
    Условия:
        1) h должно быть целым числом и должно быть больше 0 
        и меньше длины actual_lst.
        2) crit должен принимать только значения, указанные выше.
        4) Каждое значение actual_lst, pred1_lst и pred2_lst 
        должно быть числовым. Пропуски не принимаются.
        5) значение power должна быть числом.
    """
    # все параметры для инициализации публичных атрибутов
    # задаем в методе __init__
    def __init__(self, crit='MSE', power=2, h=1, seasonal_period=1):
        # строка, определяющая критерий
        self.crit = crit
        # количество шагов вперед
        self.h = h
        # степень в функции для взвешивания ошибок 
        # (имеет смысл, только когда crit='poly')
        self.power = power
        # количество периодов в полном сезонном цикле, 
        # используется только при расчете MASE
        self.seasonal_period = seasonal_period
        # предварительная установка признака того, что 
        # входные данные являются массивами NumPy
        self.numpy_flag = True

        # передача функции re_compile() соответствующего регулярного 
        # выражения для проверки, является ли каждое значение 
        # входных списков числовым значением
        self.comp = re_compile('[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?')

    # метод, возвращающий True, если значение соответствует 
    # шаблону регулярного выражения
    def check_regex_matching(self, string):
        # проверка соответствия строки s шаблону 
        # регулярного выражения comp
        if self.comp.match(string) is None:
            # если да, то возвращает признак, указывающий на то, 
            # содержит ли строка только цифры
            return string.isdigit()

        return True

    # метод проверки наличия ошибок во входных данных
    def error_check(self, actual_lst, pred1_lst, pred2_lst):
        # установка признака ошибки в 0
        rt = 0
        # присвоение переменной сообщения пустого значения
        msg = ""

        # проверяем, является ли значение self.h целочисленным
        if not isinstance(self.h, int):
            # установка признака ошибки в -1
            rt = -1
            # сообщение о том, что h не является целочисленным
            msg = "The type of the number of steps ahead (h) is not an integer."

            # возвращение признака ошибки и сообшения об ошибке
            return rt, msg

        # проверка диапазона h
        if self.h < 1:
            # если h отрицателен, то установка признака ошибки 
            # и соответствующего сообщения
            rt = -1
            msg = "The number of steps ahead (h) is not large enough."

            # возвращение признака ошибки и сообщения об ошибке
            return rt, msg

        # вычисление длины входных данных
        len_act = len(actual_lst)
        len_p1 = len(pred1_lst)
        len_p2 = len(pred2_lst)
        # проверка того, равны ли длины фактических и прогнозируемых значений
        if len_act != len_p1 or len_p1 != len_p2 or len_act != len_p2:
            # если нет, то установка признака ошибки и соответствующего сообщения
            rt = -1
            msg = "Lengths of actual_lst, pred1_lst and pred2_lst do not match."

            # возвращение признака ошибки и сообщения об ошибке
            return rt, msg

        # проверка того, не превышает ли h длину входных данных
        if self.h >= len_act:
            # если нет, то установка признака ошибки и соответствующего сообщения
            rt = -1
            msg = "The number of steps ahead is too large."

            # возвращение признака ошибки и сообщения об ошибке
            return rt, msg

        # проверка на правильность значения критерия
        if self.crit not in ['MSE','MAPE','MAD','MAE','MASE','MRAE','SMAPE','poly','ALL']:
            # если нет, то установка признака ошибки и соответствующего сообщения
            rt = -1
            msg = "The criterion is not supported."

            # возвращение признака ошибки и сообщения об ошибке
            return rt, msg

        # если входные данные не являются массивами NumPy, т.е. являются списками
        if not (isinstance(actual_lst, np.ndarray)
                and isinstance(pred1_lst, np.ndarray)
                and isinstance(pred2_lst, np.ndarray)):
            # если данные не NumPy, то выставляется флаг
            self.numpy_flag = False

            # то в цикле проверяем каждое из значений списков
            for actual, pred1, pred2 in zip(actual_lst, pred1_lst, pred2_lst):
                # на предмет, являются ли они числовыми значениями
                is_actual_ok = self.check_regex_matching(str(abs(actual)))
                is_pred1_ok = self.check_regex_matching(str(abs(pred1)))
                is_pred2_ok = self.check_regex_matching(str(abs(pred2)))
                # если не являются, то установка признака ошибки
                # и соответствующего сообщения
                if not (is_actual_ok and is_pred1_ok and is_pred2_ok):
                    msg = ("An element in the actual_lst, pred1_lst" + 
                           "or pred2_lst is not numeric.")
                    rt = -1

                    # возвращение признака ошибки и сообщения об ошибке
                    return rt, msg

        # если ошибок нет, то возвращение признака ошибки,
        # равного 0 и пустого сообщения об ошибке
        return rt, msg

    # метод, вычисляющий значения теста Диболда-Мариано 
    # для заданных наборов прогнозов
    def db_test(self, actual_lst, pred1_lst, pred2_lst) -> object:
        """
        actual_lst: список реальных значений зависимой переменной
        pred1_lst: первый список прогнозов
        pred2_lst: второй список прогнозов
        Условия:
            1) длины actual_lst, pred1_lst и pred2_lst должны быть равны
            2) actual_lst, pred1_lst и pred2_lst должны быть либо 
            числовыми массивами numpy, либо списками, каждое значение 
            которых должно быть числовым. Пропуски не принимаются.
        Возвращаемое значение:
            именованный кортеж(named tuple) из 2 элементов:
            1) DM :  тестовая статистика DM-теста;
            2) p_value: p-значение DM-теста.
        """
        # создание пустых списков
        e1_lst = []
        e2_lst = []
        d_lst = []
        # проверка на ошибки во входных данных
        error_code = self.error_check(actual_lst, pred1_lst, pred2_lst)
        # выдача соответствующей ошибки, если есть признак ошибки
        if error_code[0] == -1:
            raise SyntaxError(error_code[1])

        # если входные данные не являются массивами NumPy
        # (т.е. являются списками)
        if not self.numpy_flag:
            # преобразовываем каждое значение списка в вещественное число
            actual_lst = np.array(actual_lst).astype(np.float32).tolist()
            pred1_lst = np.array(pred1_lst).astype(np.float32).tolist()
            pred2_lst = np.array(pred2_lst).astype(np.float32).tolist()

        # длина списков (в виде действительного числа)
        T = float(len(actual_lst))

        # малое значение, не равное нулю, чтобы избежать 
        # получения ошибки деления на нуль
        LITTLE_VALUE = 0.000001

        # расчет значений теста Диболда-Мариано в 
        # соответствии с различными критериями:

        # если критерий - MSE
        if self.crit == 'MSE':
            # в цикле перебираем значения элементов входных данных
            for actual, p1, p2 in zip(actual_lst, pred1_lst, pred2_lst):
                # вычисляем метрику качества MSE для каждого из элементов 
                # и добавляем в соответствующие списки метрик
                e1_lst.append((actual - p1) ** 2)
                e2_lst.append((actual - p2) ** 2)
                
        # если критерий - MAE или MAD
        elif self.crit == 'MAE' or self.crit == 'MAD':
            # в цикле перебираем значения элементов входных данных
            for actual, p1, p2 in zip(actual_lst, pred1_lst, pred2_lst):
                # вычисляем метрику качества MAE для каждого из элементов 
                # и добавляем в соответствующие списки метрик
                e1_lst.append(abs(actual - p1))
                e2_lst.append(abs(actual - p2))
                
        # если критерий -  MAPE
        elif self.crit == 'MAPE':
            # в цикле перебираем значения элементов входных данных
            for actual, p1, p2 in zip(actual_lst, pred1_lst, pred2_lst):
                # в знаменатель идет значение actual
                dv = actual
                # если значение actual равно нулю
                if not actual:
                    # присваиваем переменной, идущей в знаменатель, малое значение,
                    # не равное нулю, чтобы избежать получения ошибки деления на ноль
                    dv = LITTLE_VALUE

                # вычисляем метрику качества MAPE для каждого из элементов 
                # и добавляем в соответствующие списки метрик
                e1_lst.append(100 * abs((actual - p1) / dv))
                e2_lst.append(100 * abs((actual - p2) / dv))
                
        # если критерий - poly
        elif self.crit == 'poly':
            # в цикле перебираем значения элементов входных данных
            for actual, p1, p2 in zip(actual_lst, pred1_lst, pred2_lst):
                # вычисляем метрику с использованием степенной 
                # функции для взвешивания ошибок и добавляем 
                # в соответствующие списки метрик
                e1_lst.append((actual - p1) ** self.power)
                e2_lst.append((actual - p2) ** self.power)

        # если критерий - MASE
        # числителем тут будет абсолютная ошибка прогноза, 
        # а знаменателем - средняя абсолютная ошибка,
        # полученная на обучающей выборке с помощью
        # одношагового метода наивного сезонного прогноза
        elif self.crit == 'MASE':
            # в цикле перебираем значения элементов входных данных
            for actual, p1, p2 in zip(actual_lst, pred1_lst, pred2_lst):
                # одношаговый метод наивного сезонного прогноза, 
                # это значение actual_lst[:-self.seasonal_period]
                # вычисление средней абсолютной ошибки, полученной 
                # с помощью одношагового метода наивного сезонного
                # прогноза, идущей в знаменатель:
                dv = np.mean(np.abs(np.array(actual_lst[self.seasonal_period:]) -
                                    np.array(actual_lst[:-self.seasonal_period])))
                # вычисляем метрику качества MASE для каждого из элементов 
                # и добавляем в соответствующие списки метрик
                e1_lst.append(abs((actual - p1) / dv))
                e2_lst.append(abs((actual - p2) / dv))
                
        # если критерий - MRAE
        elif self.crit == 'MRAE':
            # в цикле перебираем значения элементов входных данных
            for cnt, (actual, p1, p2) in enumerate(
                zip(actual_lst, pred1_lst, pred2_lst)):
                # если это первая итерация
                if cnt == 0:
                    # запоминаем значение текущего элемента из actual_lst
                    actual_pre = actual
                    # и переходим к следующей итерации цикла
                    continue

                # формируем знаменатель как разницу текущего значения 
                # из actual_lst и прошлого
                dv = actual - actual_pre
                # если найденное значение равно нулю, заменяем его на малое 
                # значение, не равное нулю, во избежании ошибки деления на нуль
                if not dv:
                    dv = LITTLE_VALUE

                # вычисляем метрику качества MRAE для каждого из элементов и
                # добавляем в соответствующие списки метрик
                e1_lst.append(abs((actual - p1) / dv))
                e2_lst.append(abs((actual - p2) / dv))
                # запоминаем значение текущего элемента из actual_lst
                actual_pre = actual
                
        # если критерий - SMAPE
        elif self.crit == 'SMAPE':
            # в цикле перебираем значения элементов входных данных
            for actual, p1, p2 in zip(actual_lst, pred1_lst, pred2_lst):
                # формируем первый знаменатель
                dv1 = abs(actual + p1)
                # если их значение равно нулю, заменяем его
                # на малое, но ненулевое значение
                if not dv1:
                    dv1 = LITTLE_VALUE

                # формируем второй знаменатель
                dv2 = abs(actual + p2)
                if not dv2:
                    dv2 = LITTLE_VALUE

                # вычисляем метрику качества SMAPE для каждого из элементов 
                # и добавляем в соответствующие списки метрик
                e1_lst.append(200 * abs((actual - p1) / dv1))
                e2_lst.append(200 * abs((actual - p2) / dv2))

        # если критерий - ALL, то вычисляем значения тестов Диболда-Мариано 
        # со всеми критериями MSE, MAPE, MAE и т.д.
        # в данном случае возвращемое значение будет словарем с соответствующими 
        # ключами и значениями - именованными кортежами, возвращаемыми 
        # каждым отдельным методом
        if self.crit == 'ALL':
            # создание пустого словаря
            rt = {}
            # создание списка с именами всех метрик
            cr = ['MSE', 'MAPE', 'MAE', 'MASE', 'MRAE', 'SMAPE', 'poly']
            # прохождение в цикле по этому списку
            for i in cr:
                # рекурсивное создание экземпляра класса DieboldMarianoTest
                # с соответствующей метрикой в текущей итерации
                dmt = DieboldMarianoTest(crit=i)
                # расчет метрики теста Диболда-Мариано с соответствующей метрикой
                # и занесение ее в словарь результатов
                rt[i] = dmt.db_test(actual_lst, pred1_lst, pred2_lst)

            # возращаем в качестве результата словарь
            return rt

        # если критерий был не ALL, вычисляем попарно разницы 
        # найденных метрик для каждого из элементов
        # для каждого момента времени
        for e1, e2 in zip(e1_lst, e2_lst):
            d_lst.append(e1 - e2)

        # вычисляем среднее значение
        mean_d = np.array(d_lst).mean()

        # находим автоковариацию, используя соответствующую функцию из statsmodels
        d_cov = sm.tsa.acovf(d_lst, nlag=self.h - 1, fft=True)
        # вычисляем промежуточное значение при расчете тестовой статистики DM-теста
        V_d = (d_cov[0] + 2 * d_cov[1:].sum()) / len(d_lst)
        # вычисляем статистику DM-теста
        DM_stat = V_d ** (-0.5) * mean_d

        # реализовываем модификацию теста, предложенной Харви и др. в 1997 г.

        # вычисляем поправку Харви
        harvey_adj = ((T + 1 - 2 * self.h + self.h * (self.h - 1) / T) / T) ** 0.5
        # вычисляем статистику DM-теста, скорректированного с учетом поправки Харви
        DM_stat = harvey_adj * DM_stat
        # вычисляем p-значение
        p_value = 2 * t.cdf(-abs(DM_stat), df=T-1)

        # создаем экземпляр именованного кортежа для возврата
        # возвращаем именованный кортеж с найденными значениями теста Диболда-Мариано
        return namedtuple('dm_return', ['DM', 'p_value'])(DM_stat, p_value)
