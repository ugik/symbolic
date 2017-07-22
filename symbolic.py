'''
Copyright (C) 2017 G.Kassabgi <https://github.com/ugik>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


import urllib.request, json 
import copy

# convenience functions

# determine if a subset is first of its kind in the subsets list
def subset_first(subset, subsets):
    # make a copy as clear_offset() alters the object
    subset_clear = copy.deepcopy(subset)
    subset_clear.clear_offset()
    first = True
    for i,s in enumerate(subsets):
        s_clear = copy.deepcopy(s)
        s_clear = s_clear.clear_offset()
        if str(s_clear) == str(subset_clear):
            if subsets[i].get_offset('',0) < subset.get_offset('',0):
                first = False
                break
  
    return first

# find intersection between 2 masks
def mask_intersection(mask1, mask2, debug=False):
    mask = []
    # loop through subsets in outer mask
    for outer_position, outer_mask in enumerate(mask1):
        # loop through subsets in inner mask
        for inner_position, inner_mask in enumerate(mask2):
            if debug: print ('comparing', outer_mask, inner_mask)
            if str(outer_mask) == str(inner_mask):
                mask.append(outer_mask)
            elif len(outer_mask) == len(inner_mask):
                # if subsets are equal length then see if they match in the abstract
                if outer_mask.mask(inner_mask, offsets=False):
                    mask.append(outer_mask.mask(inner_mask, offsets=False))
    
    # normalize lists
    refactored_mask = []
    for m in mask:
        if type(m) == list:
            for m_item in m:
                refactored_mask.append(m_item)
        elif type(m) == Symbolic:
            refactored_mask.append(m)

    # remove dups
    dedup_mask = []
    for m in refactored_mask:
        if str(m) not in str(dedup_mask):
            dedup_mask.append(m)

    return dedup_mask


# In[3]:

# symbolic structure: a list, each element a tuple of symbol (str) and a symbolic structure: [('a', [('foo', None)]
#
class Symbolic:

    # representation of placeholder symbol
    WILDCARD = '*'
    OFFSET = '_'
    
    def __init__(self, symbols=None):
        if type(symbols) == list:
            self.symbols = symbols
        elif type(symbols) == str:
            self.symbols = symbols.split(' ')
        elif type(symbols) == tuple:
            self.symbols = [symbols]
        else:
            self.symbols = None
        
        if self.symbols:
            # transform into list of tuples
            for i in range(0, len(self.symbols)):
                s = self.symbols[i]
                # handle list
                if type(s) == list:
                    self.symbols[i] = Symbolic(s)
                # if symbol is not already a symbolic structure
                elif type(s) != Symbolic and type(s) != tuple:
                    self.symbols[i] = (s, None)


    # produce all unique subsets for a list and their relative offset position
    def subsets(self, offsets=True):
        if offsets:
            self.add_offset()
            
        # list of subsets
        subsets = []
        for i, s in enumerate(self.symbols):
            for ii in range(1, len(self.symbols)+1):
                if ii >i:
                    subset = Symbolic(self.symbols[i:ii])
                    # each subset is a Symbolic structure
                    if not subset.get_symbol(self.OFFSET, partial=True):
                        subsets.append(subset)
            
        # subsets is a list of subsets and their offsets
        return subsets

    # add offset to symbol structure using OFFSET prefix
    def add_offset(self):
        for i, s in enumerate(self.symbols):
            if (not s[1] or not s[1].get_symbol(self.OFFSET, partial=True)) and self.OFFSET not in s[0]:
                # add offset symbol
                self.add_symbolic('', self.OFFSET +str(i), position=i)
            
        return self

    # clear offset in symbol structure
    def clear_offset(self):
        for i, s in enumerate(self.symbols):
            if s[1] and s[1].get_symbol(self.OFFSET, partial=True):
                # delete offset symbol
                s[1].del_symbol(self.OFFSET, partial=True)
            
        return self

    # get symbol offset
    def get_offset(self, element, position=-1, partial=False):
        s = self.get_symbol(element, position=position, partial=partial)
        if s and s[1]:
            o = s[1].get_symbol(self.OFFSET, partial=True)
            if o:
                split = o[0].split(self.OFFSET)
                if len(split) >1 and split[1].isdigit():
                    return split[1]

        
    # add symbol to structure
    def add_symbol(self, symbol):
        if self.symbols:
            self.symbols.append((symbol, None))
        elif symbol:
            self.symbols = [(symbol, None)]
        else:
            self.symbols = []

    # add symbolic structure to a symbol
    def add_symbolic(self, element, symbol, position=-1):
        
        if element in [e[0] for e in self.symbols] or position>-1:
            for n,s in enumerate(self.symbols):
                if s[0] == element and (n == position or position<0) or (n == position and position>-1):
                    # handle case where symbol cantains no symbolic structure
                    if not s[1]:
                        self.symbols[n] = (self.symbols[n][0], Symbolic(symbol))
                    else:
                        self.symbols[n][1].add_symbol(symbol)
        
    # delete a symbol, by element name or [optional] by list position, [optional] partial name
    def del_symbol(self, element, position=-1, partial=False):
            
        if element in [e[0] for e in self.symbols] or position>-1 or partial:
            for n, (s, sub) in enumerate(self.symbols):
                if not partial and element == s and                    (n == position or position<0) or (n == position and position>-1):
                    del self.symbols[n]
                elif partial and element in s and                    (n == position or position<0) or (n == position and position>-1):
                    del self.symbols[n]

    # get a symbol, by element name or [optional] by list position, [optional] partial name
    def get_symbol(self, element, position=-1, partial=False):

        if element in [e[0] for e in self.symbols] or position>-1 or partial:
            for n, (s, sub) in enumerate(self.symbols):
                if not partial and element == s and                    (n == position or position<0) or (n == position and position>-1):
                    return (s, sub)
                elif partial and element in s and                    (n == position or position<0) or (n == position and position>-1):
                    return (s, sub)

    # set a symbol, by element name or [optional] by list position, [optional] partial name
    def set_symbol(self, element, new, position=-1, partial=False):

        if element in [e[0] for e in self.symbols] or position>-1 or partial:
            for n, (s, sub) in enumerate(self.symbols):
                if not partial and element == s and                    (n == position or position<0) or (n == position and position>-1):
                    self.symbols[n] = (new, sub)
                elif partial and element in s and                    (n == position or position<0) or (n == position and position>-1):
                    self.symbols[n] = (new, sub)

    # get symbolic structure by symbol name or [optional] by list position
    def get_symbolic(self, element=None, symbol=None, position=-1):
        if position >= 0 and position <len(self.symbols):
                element = self.symbols[position][0]
            
        if element in [e[0] for e in self.symbols]:
            for n,s in enumerate(self.symbols):
                if s[0] == element:
                    # return the symbolic structure for this symbol
                    return self.symbols[n][1]
                    
    # list of elements
    def list_elements(self):
        if self.symbols:
            return [s for s in self.symbols]
        else:
            return []
        
    # similarity score between 2 symbolic structures
    def similarity(self, symbolic):
        mask = self.mask(symbolic)
        score = 0
        for m in mask:
            # longer overlapping subsets score higher
            score += len(m[0])
            
        return score 
    
    # build similarity mask between 2 symbolic structures
    # the similarity mask is a list of Symbolic structures
    def mask(self, symbolic, offsets=True, debug=False):    
        mask = []
        # copy parameter subsets so we can manipulate the list while searching
        symbolic_subsets = symbolic.subsets(offsets=offsets)
        
        if debug: print('subsets:', symbolic_subsets)
            
        # loop through our subsets
        for outer_position, outer_subset in enumerate(self.subsets(offsets=offsets)):
            for inner_position, inner_subset in enumerate(symbolic_subsets):

                match = True
                match_mask = outer_subset

                if debug: 
                    print ('0:', outer_position, outer_subset, inner_position, inner_subset, symbolic_subsets)

                first_subset = True
                # note if this is the first subset of its kind in the subset list
                if offsets and not subset_first(outer_subset, self.subsets()):
                    first_subset = False

                # compare the str of each subset's Symbolic structure to test exact match
                if str(outer_subset) != str(inner_subset):           
                    
                    # if not same length then no match
                    if len(outer_subset) != len(inner_subset):
                        match = False

                    else:
                        # if symbols are not same but same length
                        match_mask = Symbolic()
                        
                        # loop through each symbol
                        for i in range(0, len(outer_subset)):
                            symbol = outer_subset.get_symbol('', i)

                            if debug: print ('compare:', symbol[0], inner_subset.get_symbol('', i)[0])
                            
                            # for each unequal symbol
                            if str(symbol[0]) != str(inner_subset.get_symbol('', i)[0]):

                                # are their respective symbolic structures empty?
                                if not symbol[1] or not inner_subset.get_symbol('', i)[1]:
                                    match = False; break
                                
                                if debug: print ('compare::', symbol[1], inner_subset.get_symbol('', i)[1])
                                
                                # recursive call mask() to check for abstract match of each symbol in structure
                                symbolics_mask = symbol[1].mask(inner_subset.get_symbol('', i)[1])

                                # do symbolic structures return any matches?
                                if not symbolics_mask:
                                    match = False; break

                                # use mask if there's a match
                                if match:
                                    # determine if position is same
                                    positional = outer_subset.get_offset(symbol[0], position=i) == inner_subset.get_offset(inner_subset.get_symbol('', i)[0], position=i)
                                    
                                    # symbols match
                                    # add only if this is the first of this symbol in the pattern or this is positional match
                                    if first_subset or positional:
                                        match_mask.add_symbol(self.WILDCARD)

                                        # add symbolics from the match subset list
                                        for symbolics_subset in symbolics_mask:
                                            symbolics_subset.clear_offset()     
                                            # single length masks are the individual matching symbols
                                            if len(symbolics_subset) == 1:
                                                match_mask.add_symbolic(self.WILDCARD, symbolics_subset.get_symbol('', 0))
                                    
                                        # add offset if offset match
                                        if positional:
                                            match_mask.add_symbolic(self.WILDCARD, self.OFFSET +outer_subset.get_offset(symbol[0], position=i))
                                        
                                        if debug: print ('1:', match_mask)

                            # symbols are equal
                            else:
                                # determine if position is same
                                positional = outer_subset.get_offset(symbol[0], position=i) and                                    outer_subset.get_offset(symbol[0], position=i) ==                                     inner_subset.get_offset(inner_subset.get_symbol('', i)[0], position=i)

                                # symbols match
                                # add only if this is the first of this symbol in the pattern or this is positional match
                                if first_subset or positional:
                                    match_mask.add_symbol(symbol[0])
                                    if debug: print ('2:', match_mask.symbols)
                                    if positional:
                                        match_mask.add_symbolic(symbol[0], self.OFFSET +outer_subset.get_offset(symbol[0], position=i))


                if match and match_mask:
                    if debug: print ('mask:', match_mask.symbols)
                
                    mask.append(match_mask)

        return mask

    # clean representation
    def clean(self):
        r_value = []
        for s, sub in self.symbols:
            # each symbol is either a str or tuple
            if type(s) == str:
                if sub:
                    r_value.append((s, sub))
                else:
                    r_value.append(s)
            elif type(s) == tuple:
                if s[1]:
                    r_value.append(s)
                else:
                    r_value.append(s[0])                

        return "%s" % (r_value)
    
    # class representation
    def __repr__(self):
        if self.symbols:
            return "%s" % (self.clean())
        else: 
            return 'None'

    # print() representation
    def __str__(self):
        if self.symbols:
            return "%s" % (self.clean())
        else: 
            return 'None'

    # iterator
    def __iter__(self):
        return iter(self.symbols)

    def __getitem__(self, item):
         return self.symbols[item]
        
    # len() overload function
    def __len__(self):
        return len(self.list_elements())

    # override the default Equals behavior
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.similarity(other) == self.similarity(self)
        return NotImplemented

    # define a non-equality test
    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        return NotImplemented
    
    # hash function
    def __hash__(self):
        # use the hashcode of str(symbols)
        return hash(str(self.symbols))

    def __copy__(self):
        copy = Symbolic()
        copy.symbols = copy.deepcopy(self.symbols)
        return copy


# In[178]:

# Reason: using patterns for reasoning
class Reason:

    # representation of placeholder symbol
    WILDCARD = '*'
    OFFSET = '_'

    # deal with basic relations and their antithesis
    relations = [{'relation': 'is', 'anti': 'is not'}, 
                 {'relation': 'is not', 'anti': 'is'}]
    
    def __init__(self):
        # keep pattern information in a dictionary
        self.patterns = {}

    # add a pattern to our information collection
    def add_pattern(self, pattern, attribute, relation="is"):
        # generate unique key
        key = str(len(self.patterns))
        pattern.add_offset()
        self.patterns[key] = {'pattern': pattern, 'attr': attribute, 'rela': relation}

    def get_key(self, key):
        if key in self.patterns:
            return self.patterns[key]
        
    # get info for a pattern
    def get_pattern(self, pattern, debug=False):
        results = []
        for p in self.patterns:
            if debug: print (p, str(self.patterns[p]['pattern']))
            if 'pattern' in self.patterns[p] and str(self.patterns[p]['pattern']) == str(pattern):
                results.append(p)
        return results
        
    # get patterns for an attribute relation
    def get_attr(self, attribute, relation="is"):
        results = []
        for p in self.patterns:
            if 'attr' in self.patterns[p] and self.patterns[p]['attr'] == attribute and                'rela' in self.patterns[p] and self.patterns[p]['rela'] == relation:
                results.append(p)
        return results

    # return patterns attributed to an attribute
    def get_patterns(self, attribute, relation="is", debug=False):
        symbolics = []
        # list patterns that have attribute
        attr_list = self.get_attr(attribute, relation)
        # loop through patterns
        for p in attr_list:
            info = self.get_key(p)
            symbolics.append(info['pattern'])

        return {'attribute': attribute, 'relation': relation, 'patterns' : symbolics}
                
    # reason on the distinguishing symbols for an attribute
    def distinguishing(self, attribute, relation="is", debug=False):
        symbolics = []
        # list patterns that have attribute
        attr_list = self.get_attr(attribute, relation)
        # loop through patterns
        for p in attr_list:

            info = self.get_key(p)
            # make list of patterns
            symbolics.append(info['pattern'])

        mask = []
        for i,s in enumerate(symbolics[:-1]):
            mask.append(s.mask(symbolics[i+1]))
    
        if debug: 
            print ('masks', mask)
            print ('symbolics', symbolics)

        while len(mask) > 1:
            if debug: print ('reduced to', len(mask), 'masks')
            intersection = []
            for i,m in enumerate(mask[:-1]):
                if debug: 
                    print ('m', m)
                    print ('mask', mask[i+1])
                intersection.append(mask_intersection(m, mask[i+1]))
            mask = intersection

        if mask:
            return mask[0]
        else:
            return None

    
    # determine if a pattern is associated with an attribute
    # steps: 1. check for equality with patterns (or anti-patterns)
    #        2. attribute distinguishing symbols (the intersection of the attribute patterns' powerset)
    #        3. relative similarity (the avg similarity score across the attribute patterns and anti-patterns)
    #
    # returns boolean and reason for it
    def determine(self, pattern, attribute, relation="is", debug=False):
        
        # make sure pattern has offsets
        pattern.add_offset()
        
        # establish the anti-relation (eg. 'is' != 'is not')
        ar = None
        for r in self.relations:
            # find the anti-relation
            if r['relation'] == relation:
                ar = r['anti']
                if debug: print ('anti-relation:', ar)
                    
        # check to see if pattern matches one of the attribute patterns
        matching_keys = self.get_pattern(pattern)
        if matching_keys:
            for key in matching_keys:
                match = self.get_key(key)
                if debug: print ('key', match)
                # is there a match in an attribute pattern?
                if 'attr' in match and 'rela' in match and match['attr'] == attribute and match['rela'] == relation:
                    if debug: print('match', match)
                    return True, 'exact match with attribute patterns'
                # is there a match in an attribute anti-pattern?
                if 'attr' in match and 'rela' in match and match['attr'] == attribute and match['rela'] == ar:
                    if debug: print('anti-match', match)
                    return False, 'exact match with attribute anti-patterns'
        elif debug: print ('no matching patterns')

        # get the distinguishing symbols for the attribute (the intersection of its powerset) in the relation
        dis_features = self.distinguishing(attribute, relation)
        match = False
    
        if dis_features:
            for feature in dis_features:
                # mark the feature with the pattern
                mask = feature.mask(pattern, offsets=False)
    
                # confirm that every feature is in the mask
                match = False
                # check that one of the masks is found in the mask
                if mask:
                    for m in mask:
                        if str(m) == str(feature):
                            match = True
                            break
                    
                    if not match:
                        break
        
            if match:
                if debug: print ('has distinguishing features')
                return True, 'has distinguishing features'

        # get the anti-relation distinguishing symbols for the attribute (the intersection of its powerset)
        if ar:
            dis_features = self.distinguishing(attribute, ar)
            if dis_features:
                match = False
                for feature in dis_features:
                    # mark the feature with the pattern
                    mask = feature.mask(pattern, offsets=False)
    
                    # confirm that every feature is in the mask
                    match = False
                    # check that one of the masks is found in the mask
                    if mask:
                        for m in mask:
                            if str(m) == str(feature):
                                match = True
                                break
                    
                    if not match:
                        break
        
            if match:
                if debug: print ('has distinguishing features for anti-relation')
                return True, 'has distinguishing features for anti-relation'

            
        # if there's no pattern match and no distinguishing features then look for relative similarity within class
        if ar:
            perfect_score = pattern.similarity(pattern)
            rela_score = anti_score = 0
            rela_count = anti_count = 0
            # get list of pattern similarity with the relation
            rela_list = self.get_attr(attribute=attribute, relation=relation)
            for rela_pattern_key in rela_list:
                rela_pattern = self.get_key(rela_pattern_key)['pattern']
                similarity = pattern.similarity(rela_pattern)
                rela_score += similarity
                rela_count += 1
                if debug: print ('+', rela_pattern, perfect_score, similarity)
   
            # get list of pattern similarity with the anti-relation
            anti_list = self.get_attr(attribute=attribute, relation=ar)
            for anti_pattern_key in anti_list:
                anti_pattern = self.get_key(anti_pattern_key)['pattern']
                anti_similarity = pattern.similarity(anti_pattern)
                anti_score += similarity
                anti_count += 1
                if debug: print ('-', anti_pattern, perfect_score, anti_similarity)
            
            if rela_count == 0 or anti_count == 0: 
                return None, "I don't know"

            if debug: 
                print ('rela count', rela_count, 'anti count', anti_count)
                print ("rela score", float(rela_score/rela_count), "anti score", float(anti_score/anti_count))
            # determination favors the highest avg similarity score in the relation/anti-relation patterns
            if float(rela_score/rela_count) > float(anti_score/anti_count):
                return True, 'has higher similarity with attribute patterns than its anti-patterns'
            elif float(rela_score/rela_count) < float(anti_score/anti_count): 
                return False, 'has higher similarity with attribute anti-patterns than its patterns'
        
        # when all else fails None is equivalent to "I don't know"
        return None, "I don't know"


