

import json
import pandas as pd
import random

# files related to ProPara
propara_train_tsv_file = '../../datasets/propara/grids.v1.train.tsv'
propara_train_json_file = '../../datasets/propara/grids.v1.train.json'

# files related to the gold-set (for the zero shot models)
gold_analogies = '../../datasets/gold_test_set/gold_set_analogies.csv'
gold_set_distractors_csv_file = '../../pipeline/distractors_generation/gold_set_distractors/distractors.csv'

# output data files for evaluation (both binary and multiple choice for the zero-shot models)
gold_set_distractor_w_random_distractor_csv_file = 'gold_set_data_for_evaluation/gold_set_data_for_evaluation_w_distractor_w_random_distractor.csv'
data_for_evaluation_binary_task_output_filename = 'gold_set_data_for_evaluation/data_for_evaluation_binary_task.csv'
data_for_evaluation_binary_task_shuffled_output_filename = 'gold_set_data_for_evaluation/data_for_eval_balanced_shuffled.csv'
data_for_evaluation_mc_basic_output_filename = 'gold_set_data_for_evaluation/data_for_eval_mc_basic.csv'
data_for_evaluation_mc_advanced_output_filename = 'gold_set_data_for_evaluation/data_for_eval_mc_advanced.csv'

# files related to the silver-set (for fine-tuning FlanT5-small)
silver_analogies = '../../datasets/silver_training_set/silver_set_analogies.csv'
silver_set_distractors_csv_file = '../../pipeline/distractors_generation/silver_set_distractors/distractors.csv'
# output data files for evaluation (binary task for fine-tuning FlanT5-small on silver data)
silver_set_distractor_w_random_distractor_csv_file = 'silver_set_data_for_training/silver_set_data_for_training_w_distractor_w_random_distractor.csv'
data_for_training_silver_binary_task_output_filename = 'silver_set_data_for_training/data_for_training_silver_binary_task.csv'
data_for_training_silver_binary_task_shuffled_output_filename = 'silver_set_data_for_training/data_for_train_silver_balanced_shuffled.csv'



# --- Code related to ProPara files in order to integrate random target paragraphs ---


def get_paragraph_titles(filename):
    paragraph_titles = []
    f = open(filename, "r")
    lines = f.readlines()
    for line in lines:
        if "\t\tPROMPT:" not in line:
            continue
        start = line.find("\t\tPROMPT:") + len("\t\tPROMPT:")
        end = line.find("\t-")
        paragraph_title = line[start+1:end]
        paragraph_titles.append(paragraph_title)
    return paragraph_titles


def read_propara_paragraphs(filename):
    f = open(filename, "r")
    lines = f.readlines()
    data = [{} for _ in range(len(lines))]
    for idx, line in enumerate(lines):
        json_object = json.loads(line)
        para_id, texts, participants, states = json_object['para_id'], json_object['sentence_texts'], \
                                               json_object['participants'], json_object['states']
        data[idx]['para_id'], data[idx]['texts'], data[idx]['participants'], data[idx]['states'] = para_id, texts, \
                                                                                                   participants, states
    return data

def create_propara_files(propara_json_file, propara_tsv_file):
    paragraph_titles = get_paragraph_titles(propara_tsv_file)
    d = {}
    for t in paragraph_titles:
        d[t] = 1 if t not in d else d[t] + 1

    data = read_propara_paragraphs(propara_json_file)
    para_id_title_map = {}
    for i in range(len(data)):
        para_id_title_map[data[i]["para_id"]] = paragraph_titles[i]

    converted_data = [{} for _ in range(len(data))]
    for idx, sample in enumerate(data):
        para_id, para_prompt, texts = sample["para_id"], para_id_title_map[sample["para_id"]], sample["texts"]
        converted_data[idx]["para_id"], converted_data[idx]["para_prompt"], converted_data[idx][
            "texts"] = para_id, para_prompt, texts

    return converted_data

# choosing a different subject (than the source) for target paragraph
def get_data_excluding_source(data, source_paragraph_subject):
    new_data = []
    for d in data:
        if d['para_prompt'] == source_paragraph_subject:
            continue
        new_data.append(d)
    return new_data



# Multiple-choice task related functions

# Basic setup
def write_output_evaluation_data_w_randoms():
    converted_data = create_propara_files(propara_train_json_file, propara_train_tsv_file)
    df = pd.read_csv(gold_analogies)
    analogies = df[['sample_id', 'source_subject', 'source_paragraph', 'target_paragraph', 'analogy_type']]
    data_for_evaluation = pd.DataFrame(
    columns=['sample_id', 'source_paragraph', 'random1_target_paragraph', 'random2_target_paragraph', 'random3_target_paragraph',
             'analogous_target_paragraph', 'shuffled_candidates', 'analogy_type'])
    analogies = analogies.rename(columns={'target_paragraph': 'analogous_target'})


    random.seed(1)
    for index, row in analogies.iterrows():
        converted_data_excluding_source_subject = get_data_excluding_source(converted_data, row['source_subject'])
        random1, random2, random3 = random.sample(range(len(converted_data_excluding_source_subject)), 3)
        random1_paragraph = '\n'.join(converted_data_excluding_source_subject[random1]['texts'])
        random2_paragraph = '\n'.join(converted_data_excluding_source_subject[random2]['texts'])
        random3_paragraph = '\n'.join(converted_data_excluding_source_subject[random3]['texts'])

        items = [random1_paragraph, random2_paragraph, random3_paragraph, row['analogous_target']]
        random.shuffle(items)
        gt_index = items.index(row['analogous_target'])

        analogy_type = row['analogy_type']
        data_for_evaluation = data_for_evaluation.append({  'sample_id' : row['sample_id'],
                                                            'source_paragraph' : row['source_paragraph'],
                                                            'random1_target_paragraph' : random1_paragraph,
                                                            'random2_target_paragraph' : random2_paragraph,
                                                            'random3_target_paragraph' : random3_paragraph,
                                                            'analogous_target_paragraph' : row['analogous_target'],
                                                            'shuffled_candidates' : json.dumps(items),
                                                            'ground_truth' :  'C' + str(gt_index+1),
                                                            'analogy_type' : analogy_type}, ignore_index=True)
    data_for_evaluation.to_csv(data_for_evaluation_mc_basic_output_filename)

# Advanced setup
def write_output_evaluation_data_w_distractor_w_random_distractor():
    analogies = pd.read_csv(gold_set_distractor_w_random_distractor_csv_file)
    analogies = analogies.rename(columns={'new_paragraph': 'random_distractor_target_paragraph', 'random1_target_paragraph' : 'random_target_paragraph'})
    data_for_evaluation = pd.DataFrame(
        columns=['sample_id', 'source_paragraph', 'random_target_paragraph', 'random_distractor_target_paragraph', 'distractor_target_paragraph',
                 'analogous_target_paragraph', 'shuffled_candidates', 'analogy_type'])
    random.seed(1)

    for index, row in analogies.iterrows():

        items = [row['random_target_paragraph'], row['random_distractor_target_paragraph'], row['distractor_target_paragraph'], row['analogous_target_paragraph']]
        random.shuffle(items)
        gt_index = items.index(row['analogous_target_paragraph'])
        data_for_evaluation = data_for_evaluation.append({  'sample_id' : row['sample_id'],
                                                            'source_paragraph' : row['source_paragraph'],
                                                            'random_target_paragraph' : row['random_target_paragraph'],
                                                            'random_distractor_target_paragraph' : row['random_distractor_target_paragraph'],
                                                            'distractor_target_paragraph' : row['distractor_target_paragraph'],
                                                            'analogous_target_paragraph' : row['analogous_target_paragraph'],
                                                            'shuffled_candidates' : json.dumps(items),
                                                            'ground_truth': 'C' + str(gt_index + 1),
                                                            'analogy_type' : row['analogy_type']}, ignore_index=True)
    data_for_evaluation.to_csv(data_for_evaluation_mc_advanced_output_filename)





# Binary classification task related functions

def create_data_for_evaluation_binary_task():
    df = pd.read_csv(gold_set_distractor_w_random_distractor_csv_file)
    analogies = df[['sample_id',  'source_paragraph', 'random1_target_paragraph', 'distractor_target_paragraph', 'analogous_target_paragraph', 'analogy_type']]
    data_for_evaluation = pd.DataFrame(
        columns=['sample_id', 'source_paragraph', 'target_paragraph', 'ground_truth', 'type'])

    for index, row in analogies.iterrows():
        data_for_evaluation = data_for_evaluation.append({'sample_id' : row['sample_id'],
                                    'source_paragraph' : row['source_paragraph'],
                                    'target_paragraph' : row['analogous_target_paragraph'],
                                    'ground_truth' : 1,
                                    'type' : row['analogy_type']}, ignore_index=True)
        data_for_evaluation = data_for_evaluation.append({'sample_id': row['sample_id'],
                                    'source_paragraph': row['source_paragraph'],
                                    'target_paragraph': row['distractor_target_paragraph'],
                                    'ground_truth': 0,
                                    'type': "distractor"}, ignore_index=True)
        data_for_evaluation = data_for_evaluation.append({'sample_id': row['sample_id'],
                                    'source_paragraph': row['source_paragraph'],
                                    'target_paragraph': row['random1_target_paragraph'],
                                    'ground_truth': 0,
                                    'type': "random"}, ignore_index=True)

    data_for_evaluation = data_for_evaluation.sample(frac=1, random_state=1).reset_index(drop=True)
    data_for_evaluation.to_csv(data_for_evaluation_binary_task_output_filename)

    data_for_eval_label_true = data_for_evaluation[data_for_evaluation['type'].isin(['close analogy', 'far analogy'])]
    random_df = data_for_evaluation[data_for_evaluation['type'] == 'random'].sample(n=155, random_state=42)
    distractor_df = data_for_evaluation[data_for_evaluation['type'] == 'distractor'].sample(n=155, random_state=42)
    data_for_eval_label_false = pd.concat([random_df, distractor_df])
    data_for_eval_balanced = pd.concat([data_for_eval_label_true, data_for_eval_label_false])
    data_for_eval_balanced_shuffled = data_for_eval_balanced.sample(frac=1, random_state=42)
    data_for_eval_balanced_shuffled.to_csv(data_for_evaluation_binary_task_shuffled_output_filename)


def create_data_for_training_silver_binary_task():
    converted_data = create_propara_files(propara_train_json_file, propara_train_tsv_file)
    df = pd.read_csv(silver_set_distractors_csv_file)
    analogies = df[['sample_id', 'source_subject', 'source_paragraph', 'target_paragraph', 'new_paragraph']]
    analogies = analogies.rename(columns={'target_paragraph': 'analogous_target', 'new_paragraph': 'distractor_target'})
    data_for_training = pd.DataFrame(
        columns=['sample_id', 'source_paragraph', 'target_paragraph', 'ground_truth'])
    random.seed(1)

    for index, row in analogies.iterrows():
        converted_data_excluding_source_subject = get_data_excluding_source(converted_data, row['source_subject'])
        random1, _ = random.sample(range(len(converted_data_excluding_source_subject)), 2)
        random_target_paragraph = '\n'.join(converted_data_excluding_source_subject[random1]['texts'])

        data_for_training = data_for_training.append({'sample_id': row['sample_id'],
                                                          'source_paragraph': row['source_paragraph'],
                                                          'target_paragraph': row['analogous_target'],
                                                          'ground_truth': 1,
                                                          'type': "analogy"}, ignore_index=True)
        data_for_training = data_for_training.append({'sample_id': row['sample_id'],
                                                          'source_paragraph': row['source_paragraph'],
                                                          'target_paragraph': row['distractor_target'],
                                                          'ground_truth': 0,
                                                          'type': "distractor"}, ignore_index=True)
        data_for_training = data_for_training.append({'sample_id': row['sample_id'],
                                                          'source_paragraph': row['source_paragraph'],
                                                          'target_paragraph': random_target_paragraph,
                                                          'ground_truth': 0,
                                                          'type': "random"}, ignore_index=True)

        data_for_training = data_for_training.sample(frac=1, random_state=1).reset_index(drop=True)
        data_for_training.to_csv(data_for_training_silver_binary_task_output_filename)

    random_df = data_for_training[data_for_training['type'] == 'random'].sample(n=201, random_state=42)
    distractor_df = data_for_training[data_for_training['type'] == 'distractor'].sample(n=201, random_state=42)
    data_for_eval_label_true = data_for_training[data_for_training['type'] == "analogy"]
    data_for_eval_label_false = pd.concat([random_df, distractor_df])
    data_for_eval_balanced = pd.concat([data_for_eval_label_true, data_for_eval_label_false])

    data_for_eval_balanced_shuffled = data_for_eval_balanced.sample(frac=1, random_state=42)
    data_for_eval_balanced_shuffled.to_csv(data_for_training_silver_binary_task_shuffled_output_filename)





def write_silver_set_full_data():
    converted_data = create_propara_files(propara_train_json_file, propara_train_tsv_file)
    df = pd.read_csv('../../datasets/silver_training_set/silver_set_analogies_w_challenging_distractors.csv')
    print(1)
    df = df[['sample_id', 'source_id', 'source_subject',
    'source_domain', 'target_domain', 'target_subject', 'target_field', 'relations',
    'source_paragraph', 'target_paragraph', 'distractor_target_paragraph']]

    silver_full_data = pd.DataFrame(
        columns=['sample_id', 'source_id', 'source_subject',
    'source_domain', 'target_domain', 'target_subject', 'target_field', 'relations',
    'source_paragraph', 'target_paragraph', 'distractor_target_paragraph', 'random_target_paragraph'])
    random.seed(1)

    for index, row in df.iterrows():
        converted_data_excluding_source_subject = get_data_excluding_source(converted_data, row['source_subject'])
        random1, _ = random.sample(range(len(converted_data_excluding_source_subject)), 2)
        random_target_paragraph = '\n'.join(converted_data_excluding_source_subject[random1]['texts'])

        silver_full_data = silver_full_data.append({'sample_id': row['sample_id'],
                                                      'source_id' : row['source_id'],
                                                      'source_subject' : row['source_subject'],
                                                      'source_domain' : row['source_domain'],
                                                      'target_domain' : row['target_domain'],
                                                      'target_subject' : row['target_subject'],
                                                      'target_field' : row['target_field'],
                                                      'relations' : row['relations'],
                                                      'source_paragraph' : row['source_paragraph'],
                                                      'target_paragraph' : row['target_paragraph'],
                                                      'distractor_target_paragraph' : row['distractor_target_paragraph'],
                                                      'random_target_paragraph' : random_target_paragraph}, ignore_index=True)


    silver_full_data.to_csv('../../datasets/silver_training_set/silver_set_analogies_w_challenging_distractors_w_random.csv')




def write_gold_set_output_evaluation_data_with_distractor():
    converted_data = create_propara_files(propara_train_json_file, propara_train_tsv_file)
    df = pd.read_csv(gold_set_distractors_csv_file)
    analogies = df[['sample_id', 'source_subject', 'source_paragraph', 'target_paragraph', 'analogy_type', 'new_paragraph']]

    analogies = analogies.rename(columns={'target_paragraph': 'analogous_target', 'new_paragraph': 'distractor_target'})
    data_for_evaluation = pd.DataFrame(
        columns=['sample_id', 'source_paragraph', 'random1_target_paragraph', 'random2_target_paragraph', 'distractor_target_paragraph',
                 'analogous_target_paragraph', 'shuffled_candidates', 'ground_truth', 'random_paragraph',
                 'random_events_order', 'explanation', 'random_new_events_order', 'new_paragraph'])
    random.seed(1)

    for index, row in analogies.iterrows():
        converted_data_excluding_source_subject = get_data_excluding_source(converted_data, row['source_subject'])
        random1, random2 = random.sample(range(len(converted_data_excluding_source_subject)), 2)
        random_paragraph1 = '\n'.join(converted_data_excluding_source_subject[random1]['texts'])
        random_paragraph2 = '\n'.join(converted_data_excluding_source_subject[random2]['texts'])

        items = [random_paragraph1, random_paragraph2, row['distractor_target'], row['analogous_target']]
        random.shuffle(items)
        gt_index = items.index(row['analogous_target'])
        data_for_evaluation = data_for_evaluation.append({  'sample_id' : row['sample_id'],
                                                            'source_paragraph' : row['source_paragraph'],
                                                            'random1_target_paragraph' : random_paragraph1,
                                                            'random2_target_paragraph': random_paragraph2,
                                                            'distractor_target_paragraph' : row['distractor_target'],
                                                            'analogous_target_paragraph' : row['analogous_target'],
                                                            'shuffled_candidates' : json.dumps(items),
                                                            'ground_truth': 'C' + str(gt_index + 1),
                                                            'analogy_type' : row['analogy_type'],
                                                            'random_events_order': "",
                                                            "explanation": "",
                                                            "new_paragraph": "",
                                                            "random_new_events_order": ""}, ignore_index=True)

    data_for_evaluation.to_csv(gold_set_distractor_w_random_distractor_csv_file)

def write_silver_set_output_training_data_with_distractor():
    converted_data = create_propara_files(propara_train_json_file, propara_train_tsv_file)
    df = pd.read_csv(silver_set_distractors_csv_file)
    analogies = df[['sample_id', 'source_subject', 'source_paragraph', 'target_paragraph', 'new_paragraph']]

    analogies = analogies.rename(columns={'target_paragraph': 'analogous_target', 'new_paragraph': 'distractor_target'})
    data_for_evaluation = pd.DataFrame(
        columns=['sample_id', 'source_paragraph', 'random1_target_paragraph', 'random2_target_paragraph', 'distractor_target_paragraph',
                 'analogous_target_paragraph', 'shuffled_candidates', 'ground_truth', 'random_paragraph',
                 'random_events_order', 'explanation', 'random_new_events_order', 'new_paragraph'])
    random.seed(1)

    for index, row in analogies.iterrows():
        converted_data_excluding_source_subject = get_data_excluding_source(converted_data, row['source_subject'])
        random1, random2 = random.sample(range(len(converted_data_excluding_source_subject)), 2)
        random_paragraph1 = '\n'.join(converted_data_excluding_source_subject[random1]['texts'])
        random_paragraph2 = '\n'.join(converted_data_excluding_source_subject[random2]['texts'])

        items = [random_paragraph1, random_paragraph2, row['distractor_target'], row['analogous_target']]
        random.shuffle(items)
        gt_index = items.index(row['analogous_target'])
        data_for_evaluation = data_for_evaluation.append({  'sample_id' : row['sample_id'],
                                                            'source_paragraph' : row['source_paragraph'],
                                                            'random1_target_paragraph' : random_paragraph1,
                                                            'random2_target_paragraph': random_paragraph2,
                                                            'distractor_target_paragraph' : row['distractor_target'],
                                                            'analogous_target_paragraph' : row['analogous_target'],
                                                            'shuffled_candidates' : json.dumps(items),
                                                            'ground_truth': 'C' + str(gt_index + 1),
                                                            'random_events_order': "",
                                                            "explanation": "",
                                                            "new_paragraph": "",
                                                            "random_new_events_order": ""}, ignore_index=True)

    data_for_evaluation.to_csv(silver_set_distractor_w_random_distractor_csv_file)



def write_gold_set_full_data():
    df1 = pd.read_csv('../../datasets/gold_test_set/gold_set_analogies_w_challenging_distractors.csv')
    df2 = pd.read_csv('proparalogy/experiments/data_for_eval_random_distractor_multiple_choice_task.csv')
    merged_df = pd.merge(df1, df2, on='sample_id', how='inner')
    merged_df = merged_df[['sample_id', 'source_id', 'source_subject', 'source_domain', 'target_domain', 'target_subject',
                           'target_field', 'relations', 'source_paragraph_x', 'target_paragraph',
                           'analogy_type_x', 'distractor_target_paragraph_x',
                           'random_target_paragraph']]
    merged_df = merged_df.rename(columns={'source_paragraph_x': 'source_paragraph', 'analogy_type_x': 'analogy_type',
                                          'distractor_target_paragraph_x': 'distractor_target_paragraph'})
    merged_df.to_csv('../../datasets/gold_test_set/gold_set_analogies_w_challenging_distractors_w_randoms.csv')




if __name__ == '__main__':
    # write_gold_set_full_data()
    # write_silver_set_full_data()
    # # --- Create gold-set data for evaluation
    # write_gold_set_output_evaluation_data_with_distractor()
    # create_data_for_evaluation_binary_task()
    # write_output_evaluation_data_w_randoms()
    # write_output_evaluation_data_w_distractor_w_random_distractor()
    #
    # # --- Create silver-set data for training
    # write_silver_set_output_training_data_with_distractor()
    # create_data_for_training_silver_binary_task()

