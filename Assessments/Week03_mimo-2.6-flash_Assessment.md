# Assessment by mimo-2.6-flash

# Week 03 Prompting
- Awarded: 3.5b out of 5b
- Commentary: The submission covers all four tasks with genuine, well-executed experiments: three differentiated prompting frameworks, complete prediction sets with measured inference times, a novel composite metric, and proper significance testing. Tasks 1 and 2 meet their deliverables almost fully; Task 3 lacks the explicitly required implementation code and the complement/replace discussion, while Task 4 is missing the requested tables and graphs and does not analyse the model and coding-agent factors. The referenced Task 2 visualization image (task2_visual.png) could not be viewed by this model, so Task 2 was judged from the text and data files alone.

## Task 1
- Awarded: 1b   (max 1b)
- Commentary: Three non-ROSES, non-zero-shot frameworks (RTF, COT, ICIO) are chosen from https://frompting.com/frameworks/, each with a full, well-structured prompt clearly tailored to the Task 2 natural-language-to-SQL problem (schema, join rules, output-column constraints, no-hardcoding safeguards). For each framework the student explains why it was selected and what outcome is expected (e.g. RTF for strict output-format compliance, COT for an internal reasoning pass before emitting SQL, ICIO for separating shared context from per-question input). Minor drawback: the prompts and the rationale report live in one file rather than a separate data file of prompts.

## Task 2
- Awarded: 1b   (max 1b)
- Commentary: All three prompts were run against the full 155-question benchmark, producing three prediction CSVs (question, predicted_sql) that can be scored by the provided evaluator; reported accuracies (RTF 69.68%, COT 99.35%, ICIO 92.26%) are plausible given the visible SQL differences (e.g. duplicated predicates in RTF). The report records model (gpt-5.6-luna), inference time, credits and steps per prompt, compares accuracy and cost, and includes a comparison chart (task2_visual.png) covering 4 metrics - the image itself could not be viewed by this model, so it was judged only from the textual reference. Model/prompt metadata sits in the report and filenames rather than inside the CSVs, and the comparison analysis is brief, but inference times are measured and all required outputs are present.

## Task 3
- Awarded: 0.5b   (max 1b)
- Commentary: The student proposes an original composite "Prompt Score" (weighted accuracy, time, credits, steps) and reports per-prompt values (RTF 0.7121, COT 0.9861, ICIO 0.7624) that are arithmetically consistent with normalising each cost against the best observed value. However, the required source code implementing the metric is entirely missing from Week_03_Prompting (the alternative guide-format output was not used either), there is no discussion of whether the metric complements or replaces the original accuracy metric, and the defence of the weighting scheme and the prompt-comparison report are only a few lines long with the normalisation direction stated ambiguously.

## Task 4
- Awarded: 1b   (max 2b)
- Commentary: The strongest part is the statistical significance testing: two-proportion Z-tests on the 155-question accuracies yield correct figures (COT vs ICIO Z≈3.12, p<0.002 verified; COT vs RTF p<0.0001), with only a slight overstatement for ICIO vs RTF (actual Z≈5.06 rather than ">5.2"). The PS values are restated with a one-line justification each. Missing against the brief: no tables or graphs at all in Task 4, the analysis is not "detailed" (8 short lines), causal explanation barely touches the prompts themselves, and neither the model nor the coding agent is considered as a factor, nor are the PS differences themselves tested.