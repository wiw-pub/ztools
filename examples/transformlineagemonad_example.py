from openscad import *
import functools

nimport('https://raw.githubusercontent.com/wiw-pub/ztools/refs/heads/monads/src/ztools.py')
nimport('https://raw.githubusercontent.com/wiw-pub/ztools/refs/heads/monads/src/transformlineagemonad.py')

'''
This example demonstrates the use of TransformLineageMonad.
- Use of the monad as context manager (with statement in python) to auto undo transforms
- Transform captured with "native" openscad function (using solid.origin divmatrix() to capture component transform matrices)
- Transform captured with "ResultWithDelta" results, supporting component transform matrix overrides
- Transform captured with "modified native" where result is a list, where by convention the monad expects first arg is the solid.
'''

fn = 100

class MonadUtilities:
    '''
    These are "workarounds" since relying purely on before_solid.origin and after_solid.origin are not entirely invertible.
    
    TransformLineageMonad.ResultWithDelta offers an escape hatch to supply a "delta transformation matrix" for every transform step, to fully interop with multmatrix and divmatrix for building the transform lineage.
    
    When operating in TransformLineageMonad domain, TransformLineageMonad.apply_mutably() will utilize the "delta transformation matrix" to build the transformation lineage, instead of natively calculate it based on before_solid.origin and after_solid.origin.
    
    These can go into lib level (e.g., ztools), but specified here to showcase the ease for users to DIY.
    '''

    def translate_withdelta(solid, move_vec):
        '''
        translate's divmatrix seems to be non-invertible (e.g., if you translate() forward, and do divmatrix() on its origin, you will NOT return to where you had started).
        
        We can explicitly override by specifying the actual component transformation matrix (which is just 4x4 version of move_vec arg to translate()).
        '''
        replacement = solid.translate(move_vec)
        return TransformLineageMonad.ResultWithDelta(replacement, to_matrix(move_vec), [replacement])
        
    def projection_withdelta(solid):
        '''
        projection seem to "reset" solid's origin.
        
        For proper lineage construction, it needs to preserve lineage.
        
        We can override the component transform matrix with identity matrix (noop movement).
        '''
        replacement = projection(solid)
        return TransformLineageMonad.ResultWithDelta(replacement, cube(1).origin, [replacement])
        
    def rotate_extrude_withdelta(solid, angle):
        '''
        rotate_extrude makes origin the "center" of the result solid, but origin is set to identity matrix.
        
        use center() move_vec as the delta translation matrix.
        '''
        res = solid.rotate_extrude(angle)
        
        # center and axis_aligned only works on 3d solids. Raise the height to make it 3d to generate the delta transform matrix.
        tmp = solid.linear_extrude(1)
        tmp, move_vec = center(tmp, axis=[1, 1, 0])
        _, move_vec2 = axis_aligned(tmp, axis=[0, 0, 1])
        
        delta = multmatrix(to_matrix(move_vec), to_matrix(move_vec2))
        return TransformLineageMonad.ResultWithDelta(res, delta, [res])
    

def rotate_extrude_usecase():
    '''
    Imagine you have a solid somewhere away from origin, as a result of many diff + union operations.
    You need to project it to 2d, perform a rotate_extrude, and move it back to the solid's original location.
    '''

    #################################################
    # BEGIN INITIAL SETUPS 
    #################################################
    # Vertical dumbbell
    wing = cylinder(d=10, h=5, center=True)
    shaft = cylinder(d=2, h=20, center=True)
    dumbbell = wing.up(10) | wing.down(10) | shaft
    
    # Apply some movement and rotation to represent some real world operations that require you to put your object at a weird spot.
    dumbbell = dumbbell.translate([20, 20, 20]).rotx(20).roty(20)
    
    show(dumbbell.color('white'))
    #################################################
    # END INITIAL SETUPS 
    #################################################
    
    
    def compute_without_monad():
        '''
        Despite this is "less code" than compute_with_monad, it is much more error prone and manual to "restore" the transform movements.
        '''
        
        centered_dumbbell, center_vec = center(dumbbell)
        move_vec = [20, 20, 20]
        moved_dumbbell = centered_dumbbell.translate(move_vec)
        proj = projection(moved_dumbbell)
        poop = rotate_extrude(proj, 180)
        
        # Now I need to manually move the poop to the original location.
        # Requires manual inspection and compose translate/rotate/scale in the RIGHT ordering.
        
        poop_moved = poop.translate([-dim for dim in center_vec])
        
        # In this case, the "poop" is awkwardly high, because projection + rotate_extrude inadvertently "lifts" the solid when generating the solid.
        # There's no easy way to "undo" that height in respect to the pre-projection solid.
        # We can calculate that vector manually. It is error prone.
        
        # Use center again, which moves the solid based on bounding box to the z-axis as the center.
        _, poop_moved_floor_vec = center(poop_moved, axis=[0, 0, 1])
        _, orig_dumbbell_floor_vec = center(dumbbell, axis=[0, 0, 1])
        
        # Reduce the "floor" so the poop is z-aligned with the original dumbbell.
        adjust_vector = [larger_neg - smaller_neg for larger_neg, smaller_neg in zip(poop_moved_floor_vec, orig_dumbbell_floor_vec)]
        poop_moved = poop_moved.translate(adjust_vector)
        
        # This result in the same outcome as compute_with_monad.
        show(poop_moved)


    def compute_with_monad():
        '''
        This is "more code", however unwinding transform movements is automatic.
        
        Most of the 'effort' is one-time-price in implementing the _withdelta functions, for cases where solid.origin does not quite preserve transformation lineages completely. 
        
        Thankfully, this is much easier to reason about since you only need to zero-in transformation matrix for one transform, and it is all composeable in stepwise multmatrix() and divmatrix() internally in TransformLineageMonad.
        
        Note that this is bound to happen for some operations, such as unioning two solids.
        '''
        loc = dumbbell.origin
        
        # DEBUG: show cube at dumbbell.origin. Confirms the 4x4 transform matrix works.
        #tst1 = cube(20).multmatrix(loc)
        #show(tst1)
        
        # DEBUG: Shows divmatrix would undo the operation.
        #show(tst1.divmatrix(loc))
        
        # IMPORTANT: reference must exist OUTSIDE of the with context to be able to dereference it after context unwind!
        monad = TransformLineageMonad(dumbbell)
        
        with (
            monad as dum
        ):
            # All translate/rotate/scale within the with-scope will be unwind after!
            # Good for diff/union solids around the origin, and the context will restore to original position.
            
            # Center the solid around the origin.
            # center_withdelta() is already supplied in ztools lib (early experimental).
            dum_at_origin, _ = dum.apply_mutably(lambda solid: center_withdelta(solid))
            #show(dum_at_origin.solid.color('yellow'))
    
            # Final reposition to be ready for rotate_extrude. It is a 2d projection now.
            dum_ready_for_rotate_extrude, _ = dum_at_origin.apply_mutably(lambda solid: MonadUtilities.translate_withdelta(solid, [20, 20, 20]))
            #show(dum_ready_for_rotate_extrude.solid.color('cyan'))
            
            # Perform the projection to 2d, right before rotate_extrude.
            dum_ready_for_rotate_extrude, _ = dum_ready_for_rotate_extrude.apply_mutably(lambda solid: MonadUtilities.projection_withdelta(solid))
            
            # Give it height of 1 to show in render() F6.
            #show(dum_ready_for_rotate_extrude.solid.linear_extrude(1).color('blue'))
            
            # 2-layer caricature poop emoji.
            weird_pottery_looking_thing, _ = dum_ready_for_rotate_extrude.apply_mutably(lambda shape: MonadUtilities.rotate_extrude_withdelta(shape, 180))
            #show(weird_pottery_looking_thing.solid.color('orange'))
        
        # Once context exits, all the 4x4 transform matrix will unwind.
        # The result solid will "move" to the original position and orientation before context started.
        show(monad.solid.color('magenta'))
        

    # Toggle these to compare the two outcomes.
    compute_with_monad()
    #compute_without_monad()
    
# run the sample
rotate_extrude_usecase()