from __future__ import annotations 

from typing import Callable, Any, Tuple
from dataclasses import dataclass, field

from openscad import *


@dataclass
class TransformLineageMonad:
    '''
    Monad for tracking lineage of transformation (e.g., 4x4 transformation matrix, commonly used in computer graphics and robotics forward/inverse kinematics).

    Primary usage: when used as a context manager, you can auto-undo all the transforms wrapped within the context.

    Rationale: many openscad operations are origin-centric (e.g., rotate_extrude). It's a typical pattern requiring to "move" the solid to the origin, do some operations, and move them back to its original position.
    
    Having a context manager as a "pattern" minimizes half the noise in the code moving the solids around.
    '''

    # Pythonscad solid. Typically 3d, but it will also work with 2d solids since transformation matrix is 4x4 in 3d space regardless of 2d or 3d solid.
    solid: Openscad

    # Logical result of multmatrix() on all the 4x4 matrix in transformation_stack
    # This solely exists, because some solid's origin is not trustworthy due to diff/union resetting origin despite we logically "track" it thru transformation_stack.
    # Have this "cached" compute is an optimization over performing multmatrix() thru transformation_stack all the time.
    #combined_origin: list[list[float]] = field(default_factory = lambda : cube(1).origin)
    combined_origin: list[list[float]] = field(default_factory = lambda : list)
    
    '''
    Stack of transformations to end in this solid.
    If not provided, init with identity matrix.
    '''
    #transformation_stack: list[list[list[float]]] = field(default_factory = lambda : [cube(1).origin])
    transformation_stack: list[list[list[float]]] = field(default_factory = lambda : list)

    __checkpoint: int = 1

    def __post_init__(self):
        if not self.combined_origin:
            self.combined_origin = self.solid.origin
        if not self.transformation_stack:
            self.transformation_stack.append(self.solid.origin)
    
    @dataclass
    class ResultWithDelta:
        '''
        Typed result that transform_func can return, which allows overriding transform_matrix tracking behavior.
        '''
        result_solid: Openscad
        delta_transform_matrix: List[List[float]]
        transform_func_results: List[Any]

    def clone(self) -> TransformLineageMonad:
        '''
        Deep clone of this TransformLineageMonad instance.
        Clones transformation_stack entirely.
        '''
        new_stack = []
        for matrix in self.transformation_stack:
            new_stack.append([row[:] for row in matrix])
        
        new_origin = [row[:] for row in self.combined_origin]
                
        return TransformLineageMonad(self.solid, new_origin, new_stack)
        
    def undo_mutably(self) -> TransformLineageMonad:
        '''
        Mutably unwind a transformation top of stack.
        Reassigns self.solid, and modifies transformation_stack.
        '''
        if not self.transformation_stack:
            raise IndexError('transformation stack is empty. Cannot undo_mutably()')
        
        evict = self.transformation_stack.pop()
        
        self.combined_origin = divmatrix(self.combined_origin, evict)
        self.solid = self.solid.divmatrix(evict)
        return self
    
    def apply_mutably(self, transform_func: Callable[[Openscad], Openscad | List[Any] | ResultWithDelta]) -> TransformLineageMonad | Tuple[TransformLineageMonad, List[Any]]:
        '''
        Mutably apply_mutably the transform_func that operates on PyOpenScad object (of type Openscad).
        Appends the delta transformation matrix to this TransformLineageMonad instance.
        User can optionally specify a lambda that takes the output of transform_func to generate the delta transformation matrix.
        
        By convention, the transform_func is either /1/ native pythonscad func that returns a pythonscad object, or /2/ returns a collection, where resultant solid is the first element. The rest of the elements will be returned as a pass-tthru.
        
        Return monad if transform_func is native, otherwise a tuple of monad and list-of-values from transform_func.
        '''
        post_transform = transform_func(self.solid)

        replacement = None
        override_delta_transform_matrix = None
        
        # No method overloading in Python. Do scala style structural matching.
        if isinstance(post_transform, Openscad):
            is_native = True
            replacement = post_transform
                
        elif isinstance(post_transform, self.ResultWithDelta):
            
            replacement = post_transform.result_solid
            override_delta_transform_matrix = post_transform.delta_transform_matrix
            post_transform = post_transform.transform_func_results
            
        else:
            replacement = post_transform[0]

        # compute the delta transformation matrix
        delta = self.__component_matrix(replacement) if not override_delta_transform_matrix else override_delta_transform_matrix
        
        self.transformation_stack.append(delta)
        self.combined_origin = multmatrix(self.combined_origin, delta)
        self.solid = replacement

        return self, post_transform
    
    def debug_see_checkpoint(self):
        return self.__checkpoint
        
    def __component_matrix(self, replacement):
        return divmatrix(replacement.origin, self.combined_origin)
    
    def __component_matrix_naive(self, before, after) -> List[List[float]]:
        '''
        Ident the delta 4x4 matrix transformation using two solid's origin divmatrix.
        This is naive, assuming solid's origin properly preserve transformations (not always the case, such as rotate_extrude and projection which would "shift" the solid without capturing actual translations/rotations).
        '''
        return divmatrix(after.origin, before.origin)
        
    def __enter__(self):
        '''
        Remember the stack index, such that __exit__ will unwind transformations.
        '''
        self.__checkpoint = len(self.transformation_stack)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        '''
        Unwind transformations within the context.
        '''
        if exc_type or exc_val or exc_tb:
            # Let the exception be reraised.
            # Do not unwind transformations.
            return False
         
        # unwind transformations
        count = len(self.transformation_stack) - self.__checkpoint
        for _ in range(count):
            self.undo_mutably()
         
        return True