import json
import pandas as pd
data= 'data/spider/original/dev.json'
f= open(data)
dev_json= json.load(f)
psql_queries='data/spider/dev_PostgreSQL_compatible.json'
psql=open(psql_queries)
psql_data=json.load(psql)

value_list=[]
#db_list=['concert_singer', 'pets_1', 'car_1', 'flight_2', 'cre_Doc_Template_Mgt', 'course_teach', 'world_1', 'network_1', 'dog_kennels', 'battle_death',
#         'employee_hire_evaluation', 'museum_visit','orchestra','poker_player','real_estate_properties', 'singer', 'student_transcripts_tracking', 'tvshow', 'wta_1', 'voter_1']
i= 0
for q in dev_json:
    if len(value_list) == 0 :
        value_list.append(q)
    elif q["query"].lower().replace(' ', '') not in value_list[i]['query'].lower().replace(' ', ''):
        value_list.append(q)
        i += 1

value_list_df=pd.DataFrame.from_dict(value_list)
check_df=value_list_df.loc[value_list_df['db_id'].isin(['wta_1', 'student_transcripts_tracking', 'world_1'])]

psql_list_df=pd.DataFrame.from_dict(psql_data)

check_psql=psql_list_df.loc[psql_list_df['db_id'].isin(['wta_1', 'student_transcripts_tracking', 'world_1'])]
result= check_df[~(check_df['question'].isin(check_psql['question']))]

for query in value_list:
     not_in_list = [psql_query['question'] if query['question'].lower().replace(' ', '') in psql_query['question'].lower().replace(' ', '') else (print(query['question'])) for psql_query in psql_data ]



with open("data/spider/dev_no_duplicates_baseline.json", 'w') as new_file:
    json.dump(value_list, new_file, indent=4) #indent formats it into a nice cute json





