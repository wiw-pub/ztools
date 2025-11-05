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

def rotate_extrude_usecase():
    '''
    Imagine you have a solid somewhere away from origin, as a result of many diff + union operations.
    You need to project it to 2d, perform a rotate_extrude, and move it back to the solid's original location.
    '''

    # Vertical dumbbell
    wing = cylinder(d=10, h=5, center=True)
    shaft = cylinder(d=2, h=20, center=True)
    dumbbell = wing.up(10) | wing.down(10) | shaft
    
    # Apply some movement and rotation to represent some real world operations that require you to put your object at a weird spot.
    dumbbell = dumbbell.translate([20, 20, 20]).rotx(20).roty(20)
    
    
    show(dumbbell.color('white'))


    def with_monad():
        loc = dumbbell.origin
        
        # DEBUG: show cube at dumbbell.origin. Confirms the 4x4 transform matrix works.
        #tst1 = cube(20).multmatrix(loc)
        #show(tst1)
        
        # DEBUG: Shows divmatrix would undo the operation.
        #show(tst1.divmatrix(loc))
        
        
        def translate_withdelta(solid, move_vec):
            '''
            translate's divmatrix seems to be non-invertible.
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
        
        # IMPORTANT: reference must exist OUTSIDE of the with context to be able to dereference it after context unwind!
        monad = TransformLineageMonad(dumbbell)
        
        with (
            monad as dum
        ):
            # All translate/rotate/scale within the with-scope will be unwind after!
            # Good for diff/union solids around the origin, and the context will restore to original position.
    
            print(dum.combined_origin)
            rwd = center_withdelta(dum.solid)
            res, delta = rwd.result_solid, rwd.delta_transform_matrix
            print(delta)
            print(multmatrix(dum.combined_origin, delta))
            print(divmatrix(res.origin, dum.combined_origin))
    
            
            # Center the solid around the origin.
            dum_at_origin, _ = dum.apply_mutably(lambda solid: center_withdelta(solid))
            show(dum_at_origin.solid.color('yellow'))
    
            # Final reposition to be ready for rotate_extrude. It is a 2d projection now.
            dum_ready_for_rotate_extrude, _ = dum_at_origin.apply_mutably(lambda solid: translate_withdelta(solid, [20, 20, 20]))
            show(dum_ready_for_rotate_extrude.solid.color('cyan'))
            
            dum_ready_for_rotate_extrude, _ = dum_ready_for_rotate_extrude.apply_mutably(lambda solid: projection_withdelta(solid))
            
            # Give it height of 1 to show in render() F6.
            show(dum_ready_for_rotate_extrude.solid.linear_extrude(1).color('blue'))
            
            #print(dum_ready_for_rotate_extrude.combined_origin)
            
            # Well, it's what rotate_extrude does :)
            weird_pottery_looking_thing, _ = dum_ready_for_rotate_extrude.apply_mutably(lambda shape: shape.rotate_extrude(180))
            
            print('t stack', weird_pottery_looking_thing.transformation_stack)
            print('t origin', weird_pottery_looking_thing.combined_origin)
            print('recompose origin', functools.reduce(multmatrix(*weird_pottery_looking_thing.transformation_stack))
            print(len(weird_pottery_looking_thing.transformation_stack))
            

            show(weird_pottery_looking_thing.solid.color('orange'))
            
            print(weird_pottery_looking_thing.solid.origin)
            
            show(weird_pottery_looking_thing.solid.divmatrix(weird_pottery_looking_thing.combined_origin).color('pink'))
            
            
        
        print(len(monad.transformation_stack))
        print(monad.solid.origin)
        show(monad.solid.color('magenta'))
        
        
    with_monad()
rotate_extrude_usecase()