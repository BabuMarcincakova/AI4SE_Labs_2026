# Assessment by laguna-s-2.1

# Week 03 Prompting
- Awarded: 4b out of 5b
- Commentary: The student produced a thorough and well-structured Week 03 submission. Task 1 selects three non-trivial prompting frameworks (RTF, COT, ICIO) with detailed prompts and clear justification. Task 2 delivers full prediction CSVs with model/inference-time metadata, accuracy results, and a comparison report with visualization. Task 3 proposes a composite Prompt Score metric and computes values, but lacks a source-code implementation file and deeper justification. Task 4 performs a Z-test for statistical significance and interprets results, but omits the requested tables/graphs and discusses factors only briefly.

## Task 1
- Awarded: 1b   (max 1b)
- Commentary: The student chose three prompting frameworks (RTF, COT, ICIO) from https://frompting.com/frameworks/, explicitly avoiding ROSES and zero-shot as required. Each prompt is fully formulated with detailed structure (ROLE/TASK/FORMAT, INSTRUCTION/CONTEXT/REASONING/OUTPUT, or INSTRUCTION/CONTEXT/INPUT/OUTPUT) tailored to the Task 2 restaurant-to-SQL problem. The reason for choosing each framework is clearly explained and the source URL is cited. Both required outputs (data file with prompts and report on choices) are present in task1.md.

## Task 2
- Awarded: 1b   (max 1b)
- Commentary: The student solved the restaurant retrieval problem using all three prompts and produced three prediction CSV files (restaurants_dataset_predictions_RTF.csv, _COT.csv, _ICIO.csv) containing SQL queries for all 155 questions. Inference times are measured (RTF: 4m9s, COT: 2m50s, ICIO: 7m26s), and metadata including model (gpt-5.6-luna), credits, and step counts are recorded. The brief report in task2.md compares accuracy per prompt (COT 99.35% > ICIO 92.26% > RTF 69.68%) with a conclusion and references a visualization file (task2_visual.png). All required outputs are delivered.

## Task 3
- Awarded: 0.5b   (max 1b)
- Commentary: The student proposes a composite Prompt Score (PS) metric that combines Accuracy, Time, Credit usage, and Step count with weighted coefficients, and calculates PS values for all three prompts (RTF 0.7121, COT 0.9861, ICIO 0.7624). However, no source-code implementation file is provided, despite the output requirements explicitly asking for "a source code file or files containing the metric implementation." The argument for why this metric is good and applicable is brief, and there is no substantive discussion of whether it complements or replaces the original accuracy metric. The metric concept and computed values are sound, but the missing code deliverable and shallow justification limit the score.

## Task 4
- Awarded: 1.5b   (max 2b)
- Commentary: The student reiterates the Prompt Score metric from Task 3, reports composite scores (COT 0.9861, ICIO 0.7624, RTF 0.7121), and performs Z-tests for statistical significance, reporting Z-scores and p-values (COT vs ICIO: Z~3.12, p<0.002; ICIO vs RTF: Z>5.2, p<0.0001; COT vs RTF: p<0.0001). The interpretation of why differences arise is present (e.g., RTF's low accuracy, ICIO's high time/step overhead). However, the task explicitly requests tables and graphs to demonstrate results, and none are included in the Task 4 output. The discussion of the model and coding agent as contributing factors is also brief. The statistical analysis is a strong point, but the missing visualizations and incomplete factor analysis prevent full credit.

<!--
NOTES FOR THE GRADER (delete this comment block in the output file):
- Max points: Task 1 = 1b, Task 2 = 1b, Task 3 = 1b, Task 4 = 2b. Total = 5b.
- The overall "Awarded" score MUST equal the sum of the four task scores.
- Half-points (0.5b steps) are allowed.
- Replace <model_name> with your model label.
- Keep the structure and headings exactly as above.
-->
