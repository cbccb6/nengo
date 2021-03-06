import warnings

import numpy as np

import nengo.utils.numpy as npext
from nengo.base import NengoObject, ObjView
from nengo.params import Default, IntParam, ListParam, Parameter, StringParam
from nengo.utils.stdlib import checked_call


class OutputParam(Parameter):
    def __init__(self, default, optional=True, readonly=False):
        assert optional  # None has meaning (passthrough node)
        super(OutputParam, self).__init__(default, optional, readonly)

    def __set__(self, node, output):
        super(OutputParam, self).validate(node, output)

        # --- Validate and set the new size_out
        if output is None:
            if node.size_out is not None:
                warnings.warn("'Node.size_out' is being overwritten with "
                              "'Node.size_in' since 'Node.output=None'")
            node.size_out = node.size_in
        elif callable(output) and node.size_out is not None:
            # We trust user's size_out if set, because calling output
            # may have unintended consequences (e.g., network communication)
            pass
        elif callable(output):
            result = self.validate_callable(node, output)
            node.size_out = 0 if result is None else result.size
        else:
            # Make into correctly shaped numpy array before validation
            output = npext.array(
                output, min_dims=1, copy=False, dtype=np.float64)
            self.validate_ndarray(node, output)
            node.size_out = output.size

        # --- Set output
        self.data[node] = output

    def validate_callable(self, node, output):
        t, x = 0.0, np.zeros(node.size_in)
        args = (t, x) if node.size_in > 0 else (t,)
        result, invoked = checked_call(output, *args)
        if not invoked:
            msg = ("output function '%s' is expected to accept exactly "
                   "%d argument" % (output, len(args)))
            msg += (' (time, as a float)' if len(args) == 1 else
                    's (time, as a float and data, as a NumPy array)')
            raise TypeError(msg)

        if result is not None:
            result = np.asarray(result)
            if len(result.shape) > 1:
                raise ValueError("Node output must be a vector (got shape %s)"
                                 % (result.shape,))
        return result

    def validate_ndarray(self, node, output):
        if len(output.shape) > 1:
            raise ValueError("Node output must be a vector (got shape %s)"
                             % (output.shape,))
        if node.size_in != 0:
            raise TypeError("output must be callable if size_in != 0")
        if node.size_out is not None and node.size_out != output.size:
            raise ValueError("Size of Node output (%d) does not match size_out"
                             "(%d)" % (output.size, node.size_out))


class Node(NengoObject):
    """Provides arbitrary data to Nengo objects.

    Nodes can accept input, and perform arbitrary computations
    for the purpose of controlling a Nengo simulation.
    Nodes are typically not part of a brain model per se,
    but serve to summarize the assumptions being made
    about sensory data or other environment variables
    that cannot be generated by a brain model alone.

    Nodes can also be used to test models by providing specific input signals
    to parts of the model, and can simplify the input/output interface of a
    Network when used as a relay to/from its internal Ensembles
    (see networks.EnsembleArray for an example).

    Parameters
    ----------
    output : callable or array_like
        Function that transforms the Node inputs into outputs, or
        a constant output value.
    size_in : int, optional
        The number of dimensions of the input data parameter.
    size_out : int, optional
        The size of the output signal.
        Optional; if not specified, it will be determined based on
        the values of ``output`` and ``size_in``.
    label : str, optional
        A name for the node. Used for debugging and visualization.

    Attributes
    ----------
    label : str
        The name of the node.
    output : callable or array_like
        The given output.
    size_in : int
        The number of dimensions of the input data parameter.
    size_out : int
        The number of output dimensions.
    """

    output = OutputParam(default=None)
    size_in = IntParam(default=0, low=0)
    size_out = IntParam(default=None, low=0, optional=True)
    label = StringParam(default=None, optional=True)
    probeable = ListParam(default=['output'])

    def __init__(self, output=Default,
                 size_in=Default, size_out=Default, label=Default):
        self.size_in = size_in
        self.size_out = size_out
        self.label = label
        self.output = output  # Must be set after size_out; may modify size_out
        self.probeable = Default

    def __getitem__(self, key):
        return ObjView(self, key)

    def __len__(self):
        return self.size_out
