# discretestats.py
# Copyright (C) 2015 Tim Woodford.
# Deal with statistics in continuous distributions & discretization of variables.

from __future__ import division
from math import log, exp

def discretize(values, minimum, bucket_size):
    """
    Put each continuous value in values into discrete buckets.

    >>> discretize([1,2,3,4,5], 0, 1)
    [0, 1, 1, 1, 1, 1]
    >>> discretize([0,0], 1, 1)
    Traceback (most recent call last):
        ...
    Exception: Smallest value is less than minimum!
    >>> discretize([1,2,3,4,5,6,7,8,9,10], 0, 2)
    [1, 2, 2, 2, 2, 1]
    >>> discretize([9, 10, 11, 12, 13, 14], 0, 2)
    [0, 0, 0, 0, 1, 2, 2, 1]

    Args:
        values: an array of continuous values
        minimum: the minimum allowable continuous value
        bucket_size: the "width" of each bucket

    Returns:
        An array of buckets, with each array value indicating 
        the number of input values that fell into the bucket.
    """
    vals = list(values)
    vals.sort()
    if len(vals) == 0:
        return [0]
    elif vals[0] < minimum:
        raise Exception("Smallest value is less than minimum!")
    else:
        ret = []
        minimum += bucket_size
        while vals[0] >= minimum:
            minimum += bucket_size
            ret.append(0)
        count = 0
        for val in vals:
            if val >= minimum:
                ret.append(count)
                count = 0
                minimum += bucket_size
            count += 1
        if count > 0:
            ret.append(count)
        return ret

def laplace_smoothing(in_buckets, smoothing_param=1):
    """
    Do Laplace Smoothing on a set of discrete buckets representing a set of observations.

    Laplace smoothing accounts for the fact that the probability associated 
    with a certain category may be nonzero, even if that specific category 
    outcome has not been observed yet.

    See https://en.wikipedia.org/wiki/Laplace_smoothing for more information.

    Args:
        in_buckets: the raw number of observed occurances for each category
        smoothing_param: determines how much smoothing should occur.  A value of zero gives 
        you no smoothing.  The value should probably be between 0 and 1.

    Return:
        The probabilities associated with each category
    """
    d = len(in_buckets)
    N = sum(in_buckets)
    return [(x + smoothing_param)/(N + smoothing_param*d) for x in in_buckets]

def multinomial_bayes(observed, multinomial_p, prev_p):
    """
    Find the probability of an event given a multinomial feature vector.

    This uses the assumptions of a Naive Bayes classifier (see Wikipedia for more).  It uses 
    a multinomial distribution gathered from previous data, the observed feature vector, and 
    the prior probability of the event.

    See https://en.wikipedia.org/wiki/Naive_Bayes_classifier for more information.

    Args:
        observed: The observation vector - contains a number corresponding to each value in 
        the multinomial distribution vector.
        multinomial_p: The multinomial distribution vector - contains probabilities for the 
        outcome event given the features in the observation vector.
        prev_p: the prior distribution of the outcome event.

    Return:
        The probability of the outcome event, given the observation
    """
    ret = prev_p
    for i, obs in enumerate(observed):
        ret *= multinomial_p[i]*obs
    return ret
