My idea is as following:

Since we compare different prompt frameworks, we should calculate new metric based on prompt result and best result. Accuracy of output is the most important metric, but other should be considered as well. This new metric Prompt Score (PS) would be combination of number of metrics, each given its own weight.

We will consider:
Accuracy (a)
Time (t) - prompt time / best prompt time
Credit used (c) - prompt credit usage / best prompt credit usage
Step count (s) - prompt steps number / best prompt steps number

$$
PS = a \cdot 0.6 + t \cdot 0.2 + c \cdot 0.15 + s \cdot 0.05
$$

For all prompts metric would be:
RTF -> 0.7121
COT -> 0.9861
ICIO -> 0.7624

Weights can be modified for more accurate result, but this is mainly for example.