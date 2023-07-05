import pandas as pd
from tqdm import tqdm
from sklearn.preprocessing import MinMaxScaler

train = pd.read_csv("new_data/train.csv")
train_target = pd.read_csv('new_data/train_target.csv')
train = train.merge(train_target, on='id')
test = pd.read_csv("new_data/test.csv")

df = pd.concat([train, test], sort=False, axis=0)
# 特征工程
df['missing'] = (df == -1).sum(axis=1).astype(float)  # 统计每行中为-999的个数
df['bankCard'] = df['bankCard'].fillna(value=0)  # bankCard存在空值
# 删除重复列
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
# 类别组合特征
count = 0
for c in duplicated_features:
    if count == 0:
        df['new_ind' + str(-1)] = df[c].astype(str) + '_'
        count += 1
    else:
        df['new_ind' + str(-1)] += df[c].astype(str) + '_'
for c in ['new_ind' + str(-1)]:
    d = df[c].value_counts().to_dict()
    df['%s_count' % c] = df[c].apply(lambda x: d.get(x, 0))
df.drop(columns=['new_ind' + str(-1)], inplace=True)

df = df.drop(columns=duplicated_features)
print(df.shape)

no_features = ['id', 'target'] + ['bankCard', 'residentAddr', 'certId', 'dist', 'new_ind1', 'new_ind2']
features = []
numerical_features = ['lmt', 'certValidBegin', 'certValidStop', 'missing']  # 不是严格意义的数值特征，可以当做类别特征
categorical_features = [fea for fea in df.columns if fea not in numerical_features + no_features]

group_features1 = [c for c in categorical_features if 'x_' in c]  # 匿名
group_features2 = ['bankCard', 'residentAddr', 'certId', 'dist']  # 地区特征
group_features3 = ['lmt', 'certValidBegin', 'certValidStop']  # 征信1

group_features4 = ['age', 'job', 'ethnic', 'basicLevel', 'linkRela']  # 基本属性
group_features5 = ['ncloseCreditCard', 'unpayIndvLoan', 'unpayOtherLoan', 'unpayNormalLoan', '5yearBadloan']
# 重要特征+其他组合
# group_features5 = group_features1 + ['lmt']
# group_features6 = group_features1 + ['certValidBegin']
# group_features7 = group_features1 + ['lmt', 'certValidBegin']
#
# group_features8 = group_features2 + ['lmt']
# group_features9 = group_features2 + ['certValidBegin']
# group_features10 = group_features2 + ['lmt', 'certValidBegin']
#
# group_features11 = group_features4 + ['lmt']
# group_features12 = group_features4 + ['certValidBegin']
# group_features13 = group_features4 + ['lmt', 'certValidBegin']

group_features = [
    group_features1, group_features2, group_features3, group_features4,
    group_features5,
    # group_features6, group_features7, group_features8,
    # group_features9, group_features10, group_features11, group_features12,
    # group_features13
]

for index, ind_features in enumerate(group_features):
    index += 1
    count = 0
    for c in ind_features:
        if count == 0:
            df['new_ind' + str(index)] = df[c].astype(str) + '_'
            count += 1
        else:
            df['new_ind' + str(index)] += df[c].astype(str) + '_'
    for c in ['new_ind' + str(index)]:
        d = df[c].value_counts().to_dict()
        df['%s_count' % c] = df[c].apply(lambda x: d.get(x, 0))
    df.drop(columns=['new_ind' + str(index)], inplace=True)

# 数值特征处理
df['certValidPeriod'] = df['certValidStop'] - df['certValidBegin']
# 类别特征处理

# 特殊处理
# bankCard 5991
# residentAddr 5288
# certId 4033
# dist 3738
cols = ['bankCard', 'residentAddr', 'certId', 'dist']
# 计数
for col in cols:
    df['{}_count'.format(col)] = df.groupby(col)['id'].transform('count')

# 对lmt进行mean encoding
for fea in tqdm(cols):
    grouped_df = df.groupby(fea).agg({'lmt': ['mean', 'median']})
    grouped_df.columns = [fea + '_' + '_'.join(col).strip() for col in grouped_df.columns.values]
    grouped_df = grouped_df.reset_index()
    # print(grouped_df)
    df = pd.merge(df, grouped_df, on=fea, how='left')
df = df.drop(columns=cols)  # 删除四列

# cols = ['certValidPeriod', 'age', 'job', 'ethnic', 'basicLevel',
#         'linkRela']
# for col in cols:
#     df['{}_count'.format(col)] = df.groupby(col)['id'].transform('count')

# dummies
df = pd.get_dummies(df, columns=categorical_features)
df.head().to_csv('tmp/df.csv', index=None)
print("df.shape:", df.shape)

features = [fea for fea in df.columns if fea not in no_features]
train, test = df[:len(train)], df[len(train):]


def load_data():
    return train, test, no_features, features
