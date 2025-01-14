import pynusmv
import sys
import pprint
from pynusmv_lower_interface.nusmv.parser import parser 
from collections import deque

specTypes = {'LTLSPEC': parser.TOK_LTLSPEC, 'CONTEXT': parser.CONTEXT,
    'IMPLIES': parser.IMPLIES, 'IFF': parser.IFF, 'OR': parser.OR, 'XOR': parser.XOR, 'XNOR': parser.XNOR,
    'AND': parser.AND, 'NOT': parser.NOT, 'ATOM': parser.ATOM, 'NUMBER': parser.NUMBER, 'DOT': parser.DOT,

    'NEXT': parser.OP_NEXT, 'OP_GLOBAL': parser.OP_GLOBAL, 'OP_FUTURE': parser.OP_FUTURE,
    'UNTIL': parser.UNTIL,
    'EQUAL': parser.EQUAL, 'NOTEQUAL': parser.NOTEQUAL, 'LT': parser.LT, 'GT': parser.GT,
    'LE': parser.LE, 'GE': parser.GE, 'TRUE': parser.TRUEEXP, 'FALSE': parser.FALSEEXP
}

basicTypes = {parser.ATOM, parser.NUMBER, parser.TRUEEXP, parser.FALSEEXP, parser.DOT,
              parser.EQUAL, parser.NOTEQUAL, parser.LT, parser.GT, parser.LE, parser.GE}
booleanOp = {parser.AND, parser.OR, parser.XOR, parser.XNOR, parser.IMPLIES, parser.IFF}

def spec_to_bdd(model, spec):
    """
    Given a formula `spec` with no temporal operators, returns a BDD equivalent to
    the formula, that is, a BDD that contains all the states of `model` that
    satisfy `spec`
    """
    bddspec = pynusmv.mc.eval_simple_expression(model, str(spec))
    return bddspec

def research(fsm, bddspec):
    #seguo algoritmo
    reach = None
    new = fsm.init

    while fsm.count_states(new) > 0:
        #notResp = new - bddspec
        #if fsm.count_states(notResp) > 0: #se qualcosa non rispetta
        #    return fsm.pick_one_state_random(notResp), sequence
        #sequence.append(new)
        if reach:
            reach = reach + new
            new = fsm.post(new) - reach

        else:
            reach = new
            new = fsm.post(new)


    recur = reach & bddspec

    while fsm.count_states(recur) > 0:
        reach = None
        new = fsm.pre(recur)

        while fsm.count_states(new) > 0:
            if reach:
                reach = reach + new
                if recur.entailed(reach):
                    return True
                new = fsm.pre(new) - reach
            else:
                reach = new
                if recur.entailed(reach):
                    return True
                new = fsm.pre(new) - reach

        recur = recur & reach

    return False
    
def is_boolean_formula(spec):
    """
    Given a formula `spec`, checks if the formula is a boolean combination of base
    formulas with no temporal operators. 
    """
    if spec.type in basicTypes:
        return True
    if spec.type == specTypes['NOT']:
        return is_boolean_formula(spec.car)
    if spec.type in booleanOp:
        return is_boolean_formula(spec.car) and is_boolean_formula(spec.cdr)
    return False
    
def check_GF_formula(spec):
    """
    Given a formula `spec` checks if the formula is of the form GF f, where f is a 
    boolean combination of base formulas with no temporal operators.
    Returns the formula f if `spec` is in the correct form, None otherwise 
    """
    # check if formula is of type GF f_i
    if spec.type != specTypes['OP_GLOBAL']:
        return False
    spec = spec.car
    if spec.type != specTypes['OP_FUTURE']:
        return False
    if is_boolean_formula(spec.car):
        return spec.car
    else:
        return None

def parse_react(spec):
    """
    Visit the syntactic tree of the formula `spec` to check if it is a reactive formula,
    that is whether the formula is of the form
    
                    GF f -> GF g
    
    where f and g are boolean combination of basic formulas.
    
    If `spec` is a reactive formula, the result is a pair where the first element is the 
    formula f and the second element is the formula g. If `spec` is not a reactive 
    formula, then the result is None.
    """
    # the root of a spec should be of type CONTEXT
    if spec.type != specTypes['CONTEXT']:
        return None
    # the right child of a context is the main formula
    spec = spec.cdr
    # the root of a reactive formula should be of type IMPLIES
    if spec.type != specTypes['IMPLIES']:
        return None
    # Check if lhs of the implication is a GF formula
    f_formula = check_GF_formula(spec.car)
    if f_formula == None:
        return None
    # Create the rhs of the implication is a GF formula
    g_formula = check_GF_formula(spec.cdr)
    if g_formula == None:
        return None
    return (f_formula, g_formula)

def check_react_spec(spec):
    """
    Return whether the loaded SMV model satisfies or not the GR(1) formula
    `spec`, that is, whether all executions of the model satisfies `spec`
    or not. 
    """
    """
    fsm = pynusmv.glob.prop_database().master.bddFsm
    bddspec = spec_to_bdd(fsm, spec)
    #result = research(fsm, bddspec)
    """
      # ricerca per vedere se rispetta
    # funzione che costruisce l'albero e controllo su res
    '''
    if node is not None:
        path = go_back(fsm, node, reachable)  # returns tuple of nodes
        str_path = ()
        for element in path:
            str_path = str_path + (element.get_str_values(),)
        return False, str_path
    else:
        return True, None
    '''
    fsm = pynusmv.glob.prop_database().master.bddFsm
    #bddspec = spec_to_bdd(fsm, spec)

    if parse_react(spec) == None:
        return False
    else:

        #bddspec = spec_to_bdd(fsm, spec)
        f, g = parse_react(spec)
        print(f'{f},{g}')
        bddspec_f = spec_to_bdd(fsm, f)
        bddspec_g = spec_to_bdd(fsm, g)
        gamma = (bddspec_f).not_().or_(bddspec_g)

        sol = research(fsm, gamma)
        print(f'soluzione: {sol}')
        return sol
        #research(fsm, bddspec_f)
        #return True, reachable

        #return pynusmv.mc.check_explain_ltl_spec(spec)



if len(sys.argv) != 2:
    print("Usage:", sys.argv[0], "filename.smv")
    sys.exit(1)

pynusmv.init.init_nusmv()
filename = sys.argv[1]
#filename = 'react_examples/railroad.smv'
pynusmv.glob.load_from_file(filename)
pynusmv.glob.compute_model()
type_ltl = pynusmv.prop.propTypes['LTL']
for prop in pynusmv.glob.prop_database():
    spec = prop.expr
    print(spec)
    if prop.type != type_ltl:
        print("property is not LTLSPEC, skipping")
        continue
    res = check_react_spec(spec)
    if res == None:
        print('Property is not a GR(1) formula, skipping')
    if res == True:
        print("Property is respected")
    elif res == False:
        print("Property is not respected")
        #print("Counterexample:", res[1])

pynusmv.init.deinit_nusmv()
