SET default_parallel 1;
ngrams = LOAD 'trozamon_testing/input_structured' USING PigStorage('\t') AS (ngram:chararray, year:int, count:long, volumes:long);
ngrams_group = GROUP ngrams ALL;
ngrams_count = FOREACH ngrams_group GENERATE COUNT(ngrams);
DUMP ngrams_count;
