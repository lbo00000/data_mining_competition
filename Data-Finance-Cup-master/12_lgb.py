#!/usr/bin/env python
# _*_coding:utf-8_*_

"""
@Time :    2019/10/23 20:20
@Author:  yanqiang
@File: 12_lgb.py
"""

import lightgbm as lgbm
from scipy import sparse as ssp
from sklearn.model_selection import StratifiedKFold
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import OneHotEncoder


def Gini(y_true, y_pred):
    # check and get number of samples
    assert y_true.shape == y_pred.shape
    n_samples = y_true.shape[0]

    # sort rows on prediction column
    # (from largest to smallest)
    arr = np.array([y_true, y_pred]).transpose()
    true_order = arr[arr[:, 0].argsort()][::-1, 0]
    pred_order = arr[arr[:, 1].argsort()][::-1, 0]

    # get Lorenz curves
    L_true = np.cumsum(true_order) * 1. / np.sum(true_order)
    L_pred = np.cumsum(pred_order) * 1. / np.sum(pred_order)
    L_ones = np.linspace(1 / n_samples, 1, n_samples)

    # get Gini coefficients (area between curves)
    G_true = np.sum(L_ones - L_true)
    G_pred = np.sum(L_ones - L_pred)

    # normalize to true Gini coefficient
    return G_pred * 1. / G_true


cv_only = True
save_cv = True
full_train = False


def evalerror(preds, dtrain):
    labels = dtrain.get_label()
    return 'gini', Gini(labels, preds), True


path = "new_data/"

train = pd.read_csv(path + "train.csv")
train_target = pd.read_csv(path + 'train_target.csv')
train = train.merge(train_target, on='id')
train_label = train['target']

train_id = train['id']
test = pd.read_csv(path + 'test.csv')
test_id = test['id']
train.fillna(value=0, inplace=True)  # bankCard存在空值
test.fillna(value=0, inplace=True)  # bankCard存在空值
duplicated_features = ['x_0', 'x_1', 'x_2', 'x_3', 'x_4', 'x_5', 'x_6',
                       'x_7', 'x_8', 'x_9', 'x_10', 'x_11', 'x_13',
                       'x_15', 'x_17', 'x_18', 'x_19', 'x_21',
                       'x_23', 'x_24', 'x_36', 'x_37', 'x_38', 'x_57', 'x_58',
                       'x_59', 'x_60', 'x_77', 'x_78'] + \
                      ['x_22', 'x_40', 'x_70'] + \
                      ['x_41'] + \
                      ['x_43'] + \
                      ['x_45'] + \
                      ['x_61']
train = train.drop(columns=duplicated_features)
test = test.drop(columns=duplicated_features)

NFOLDS = 5
kfold = StratifiedKFold(n_splits=NFOLDS, shuffle=True, random_state=218)

y = train['target'].values
drop_feature = [
    'id',
    'target'
]+['bankCard', 'residentAddr', 'certId', 'dist']

X = train.drop(drop_feature, axis=1)
feature_names = X.columns.tolist()
cat_features = [c for c in feature_names ]
num_features = ['lmt', 'certValidBegin', 'certValidStop']

train['missing'] = (train == -1).sum(axis=1).astype(float)
test['missing'] = (test == -1).sum(axis=1).astype(float)
num_features.append('missing')
df = pd.concat([train, test], sort=False, axis=0)
print(df)
for c in cat_features:
    print(c)
    le = LabelEncoder()
    le.fit(df[c])
    train[c] = le.transform(train[c])
    test[c] = le.transform(test[c])

enc = OneHotEncoder()
enc.fit(train[cat_features])
X_cat = enc.transform(train[cat_features])
X_t_cat = enc.transform(test[cat_features])

ind_features = [c for c in feature_names if 'x_' in c]
count = 0
for c in ind_features:
    if count == 0:
        train['new_ind'] = train[c].astype(str) + '_'
        test['new_ind'] = test[c].astype(str) + '_'
        count += 1
    else:
        train['new_ind'] += train[c].astype(str) + '_'
        test['new_ind'] += test[c].astype(str) + '_'

cat_count_features = []
for c in cat_features + ['new_ind']:
    d = pd.concat([train[c], test[c]]).value_counts().to_dict()
    train['%s_count' % c] = train[c].apply(lambda x: d.get(x, 0))
    test['%s_count' % c] = test[c].apply(lambda x: d.get(x, 0))
    cat_count_features.append('%s_count' % c)

train_list = [train[num_features + cat_count_features].values, X_cat, ]
test_list = [test[num_features + cat_count_features].values, X_t_cat, ]

X = ssp.hstack(train_list).tocsr()
X_test = ssp.hstack(test_list).tocsr()

learning_rate = 0.1
num_leaves = 15
min_data_in_leaf = 2000
feature_fraction = 0.6
num_boost_round = 10000
params = {"objective": "binary",
          "boosting_type": "gbdt",
          "learning_rate": learning_rate,
          "num_leaves": num_leaves,
          "max_bin": 256,
          "feature_fraction": feature_fraction,
          "verbosity": 0,
          "drop_rate": 0.1,
          "is_unbalance": False,
          "max_drop": 50,
          "min_child_samples": 10,
          "min_child_weight": 150,
          "min_split_gain": 0,
          "subsample": 0.9
          }

x_score = []
final_cv_train = np.zeros(len(train_label))
final_cv_pred = np.zeros(len(test_id))
for s in range(4):
    cv_train = np.zeros(len(train_label))
    cv_pred = np.zeros(len(test_id))

    params['seed'] = s

    if cv_only:
        kf = kfold.split(X, train_label)

        best_trees = []
        fold_scores = []

        for i, (train_fold, validate) in enumerate(kf):
            X_train, X_validate, label_train, label_validate = \
                X[train_fold, :], X[validate, :], train_label[train_fold], train_label[validate]
            dtrain = lgbm.Dataset(X_train, label_train)
            dvalid = lgbm.Dataset(X_validate, label_validate, reference=dtrain)
            bst = lgbm.train(params, dtrain, num_boost_round,
                             valid_sets=dvalid,
                             feval=evalerror,
                             verbose_eval=100,
                             early_stopping_rounds=100)
            best_trees.append(bst.best_iteration)
            cv_pred += bst.predict(X_test, num_iteration=bst.best_iteration)
            cv_train[validate] += bst.predict(X_validate)

            score = Gini(label_validate, cv_train[validate])
            print(score)
            fold_scores.append(score)

        cv_pred /= NFOLDS
        final_cv_train += cv_train
        final_cv_pred += cv_pred

        print("cv score:")
        print(Gini(train_label, cv_train))
        print("current score:", Gini(train_label, final_cv_train / (s + 1.)), s + 1)
        print(fold_scores)
        print(best_trees, np.mean(best_trees))

        x_score.append(Gini(train_label, cv_train))

print(x_score)
pd.DataFrame({'id': test_id, 'target': final_cv_pred / 4.}).to_csv('result/lgbm3_pred_avg.csv', index=False)
pd.DataFrame({'id': train_id, 'target': final_cv_train / 4.}).to_csv('result/lgbm3_cv_avg.csv', index=False)
