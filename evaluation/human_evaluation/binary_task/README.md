This folder consists of the files related to the human evaluation of the binary classification task. See Section 5 -- "Evaluating Humans and LLMs" in the paper <br>

* In zero-shot: "mturk_for_eval_zero_shot.csv" includes the data for evaluation, "mturk_results_zero_shot.csv" includes the annotations of the workers. <br>
In total, 100 samples, 79% accuracy, 70% agreement (std=0.045) <br>
* In supervised: "mturk_for_eval_supervised.csv" includes the data for evaluation, "mturk_results_supervised.csv" includes the annotations of the workers. <br>
In total, 40 samples (10 close analogy, 10 far analogy, 10 distractor, 10 random), 92.5% accuracy, 80% agreement (std=0.014)