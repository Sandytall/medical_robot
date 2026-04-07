#!/usr/bin/env python3
"""
Behavior Tree Executor for Mars Robot
Implements behavior trees for coordinated robot behavior management
"""
import time
import json
import threading
from typing import Dict, Any, Optional, List
from enum import Enum
from abc import ABC, abstractmethod

import rclpy
from rclpy.node import Node

try:
    import py_trees
    PY_TREES_AVAILABLE = True
except ImportError:
    PY_TREES_AVAILABLE = False
    print("py_trees not available. Install with: pip install py-trees")


class BehaviorStatus(Enum):
    """Behavior execution status"""
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


class BehaviorTreeNode(ABC):
    """Base class for behavior tree nodes"""

    def __init__(self, name: str):
        self.name = name
        self.status = BehaviorStatus.RUNNING

    @abstractmethod
    def execute(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Execute the behavior node"""
        pass

    def reset(self):
        """Reset node status"""
        self.status = BehaviorStatus.RUNNING


class ConditionNode(BehaviorTreeNode):
    """Base condition node"""

    def __init__(self, name: str, condition_func):
        super().__init__(name)
        self.condition_func = condition_func

    def execute(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        try:
            if self.condition_func(blackboard):
                return BehaviorStatus.SUCCESS
            else:
                return BehaviorStatus.FAILURE
        except Exception:
            return BehaviorStatus.FAILURE


class ActionNode(BehaviorTreeNode):
    """Base action node"""

    def __init__(self, name: str, action_func):
        super().__init__(name)
        self.action_func = action_func

    def execute(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        try:
            return self.action_func(blackboard)
        except Exception:
            return BehaviorStatus.FAILURE


class SelectorNode(BehaviorTreeNode):
    """Selector composite node - succeeds when first child succeeds"""

    def __init__(self, name: str, children: List[BehaviorTreeNode] = None):
        super().__init__(name)
        self.children = children or []
        self.current_child_index = 0

    def execute(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        while self.current_child_index < len(self.children):
            child = self.children[self.current_child_index]
            child_status = child.execute(blackboard)

            if child_status == BehaviorStatus.SUCCESS:
                self.current_child_index = 0  # Reset for next execution
                return BehaviorStatus.SUCCESS
            elif child_status == BehaviorStatus.RUNNING:
                return BehaviorStatus.RUNNING
            else:  # FAILURE
                self.current_child_index += 1

        # All children failed
        self.current_child_index = 0  # Reset for next execution
        return BehaviorStatus.FAILURE


class SequenceNode(BehaviorTreeNode):
    """Sequence composite node - succeeds when all children succeed"""

    def __init__(self, name: str, children: List[BehaviorTreeNode] = None):
        super().__init__(name)
        self.children = children or []
        self.current_child_index = 0

    def execute(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        while self.current_child_index < len(self.children):
            child = self.children[self.current_child_index]
            child_status = child.execute(blackboard)

            if child_status == BehaviorStatus.FAILURE:
                self.current_child_index = 0  # Reset for next execution
                return BehaviorStatus.FAILURE
            elif child_status == BehaviorStatus.RUNNING:
                return BehaviorStatus.RUNNING
            else:  # SUCCESS
                self.current_child_index += 1

        # All children succeeded
        self.current_child_index = 0  # Reset for next execution
        return BehaviorStatus.SUCCESS


class ParallelNode(BehaviorTreeNode):
    """Parallel composite node - runs all children simultaneously"""

    def __init__(self, name: str, children: List[BehaviorTreeNode] = None, success_threshold: int = 1):
        super().__init__(name)
        self.children = children or []
        self.success_threshold = success_threshold

    def execute(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        success_count = 0
        failure_count = 0
        running_count = 0

        for child in self.children:
            child_status = child.execute(blackboard)

            if child_status == BehaviorStatus.SUCCESS:
                success_count += 1
            elif child_status == BehaviorStatus.FAILURE:
                failure_count += 1
            else:  # RUNNING
                running_count += 1

        if success_count >= self.success_threshold:
            return BehaviorStatus.SUCCESS
        elif running_count > 0:
            return BehaviorStatus.RUNNING
        else:
            return BehaviorStatus.FAILURE


class BehaviorTreeExecutor(Node):
    """Main behavior tree executor for Mars robot"""

    def __init__(self, robot_controller, config: Dict[str, Any]):
        super().__init__('behavior_tree_executor')

        self.robot_controller = robot_controller
        self.config = config

        # Behavior tree state
        self.behavior_trees = {}
        self.current_tree = None
        self.blackboard = {}
        self.execution_active = False

        # Configuration
        self.update_rate = self.config.get('behavior_tree', {}).get('update_rate', 10.0)

        # Initialize behavior trees
        self._create_behavior_trees()

        # Timer for behavior tree execution
        self.execution_timer = self.create_timer(1.0 / self.update_rate, self.execute_behavior_tree)

        self.get_logger().info("Behavior Tree Executor initialized")

    def _create_behavior_trees(self):
        """Create behavior trees for different robot modes"""
        try:
            # Create trees for each mode
            self.behavior_trees = {
                'idle': self._create_idle_tree(),
                'manual': self._create_manual_tree(),
                'follow': self._create_follow_tree(),
                'registration': self._create_registration_tree(),
                'question': self._create_question_tree(),
                'medicine': self._create_medicine_tree(),
                'health_check': self._create_health_check_tree(),
                'emergency': self._create_emergency_tree()
            }

            self.get_logger().info("Behavior trees created successfully")

        except Exception as e:
            self.get_logger().error(f"Behavior tree creation error: {e}")

    def _create_idle_tree(self) -> BehaviorTreeNode:
        """Create behavior tree for idle mode"""
        return SelectorNode("IdleBehavior", [
            SequenceNode("RespondToGreeting", [
                ConditionNode("GreetingDetected", self._check_greeting_detected),
                ActionNode("RespondToGreeting", self._respond_to_greeting)
            ]),
            SequenceNode("RandomMovement", [
                ConditionNode("MovementTimeReached", self._check_movement_time),
                ActionNode("PerformRandomMovement", self._perform_random_movement)
            ]),
            SequenceNode("AmbientBehavior", [
                ConditionNode("DisplayUpdateTime", self._check_display_update_time),
                ActionNode("UpdateAmbientDisplay", self._update_ambient_display)
            ]),
            ActionNode("Rest", self._idle_rest)
        ])

    def _create_manual_tree(self) -> BehaviorTreeNode:
        """Create behavior tree for manual control mode"""
        return SequenceNode("ManualControl", [
            ConditionNode("GamepadConnected", self._check_gamepad_connected),
            ConditionNode("ManualModeActive", self._check_manual_mode_active),
            ActionNode("ProcessGamepadInput", self._process_gamepad_input),
            ActionNode("MonitorEmergencyStop", self._monitor_emergency_stop)
        ])

    def _create_follow_tree(self) -> BehaviorTreeNode:
        """Create behavior tree for follow mode"""
        return SelectorNode("FollowBehavior", [
            SequenceNode("FollowTarget", [
                ConditionNode("TargetDetected", self._check_target_detected),
                ActionNode("CalculateMovement", self._calculate_follow_movement),
                ActionNode("ExecuteMovement", self._execute_movement),
                ActionNode("UpdateCameraTracking", self._update_camera_tracking)
            ]),
            SequenceNode("SearchForTarget", [
                ActionNode("ScanArea", self._scan_for_target),
                ConditionNode("SearchTimeoutReached", self._check_search_timeout),
                ActionNode("ExitFollowMode", self._exit_follow_mode)
            ])
        ])

    def _create_registration_tree(self) -> BehaviorTreeNode:
        """Create behavior tree for patient registration"""
        return SequenceNode("PatientRegistration", [
            ActionNode("CollectPatientInfo", self._collect_patient_info),
            SequenceNode("CapturePhotos", [
                ConditionNode("FaceDetected", self._check_face_detected),
                ActionNode("CapturePhoto", self._capture_photo),
                ConditionNode("PhotoCountReached", self._check_photo_count)
            ]),
            ActionNode("SaveToDatabase", self._save_patient_data),
            ActionNode("ConfirmRegistration", self._confirm_registration)
        ])

    def _create_question_tree(self) -> BehaviorTreeNode:
        """Create behavior tree for question answering"""
        return SequenceNode("QuestionAnswering", [
            ActionNode("ListenForQuestion", self._listen_for_question),
            ConditionNode("QuestionReceived", self._check_question_received),
            ActionNode("ProcessQuestion", self._process_question),
            ActionNode("DeliverAnswer", self._deliver_answer),
            ConditionNode("FollowUpNeeded", self._check_followup_needed)
        ])

    def _create_medicine_tree(self) -> BehaviorTreeNode:
        """Create behavior tree for medicine dispensing"""
        return SequenceNode("MedicineDispensing", [
            ActionNode("GetPatientsNeedingMedicine", self._get_patients_needing_medicine),
            SequenceNode("VisitEachPatient", [
                ActionNode("ScanForCurrentPatient", self._scan_for_patient),
                SelectorNode("PatientInteraction", [
                    SequenceNode("PatientFound", [
                        ConditionNode("PatientIdentified", self._check_patient_identified),
                        ActionNode("ConfirmPatientIdentity", self._confirm_patient_identity),
                        ActionNode("CheckMedication", self._check_medication),
                        ActionNode("DispenseMedicine", self._dispense_medicine)
                    ]),
                    SequenceNode("PatientNotFound", [
                        ActionNode("CallPatientName", self._call_patient_name),
                        ConditionNode("CallTimeoutReached", self._check_call_timeout),
                        ActionNode("MoveToNextPatient", self._move_to_next_patient)
                    ])
                ])
            ])
        ])

    def _create_health_check_tree(self) -> BehaviorTreeNode:
        """Create behavior tree for health assessment"""
        return SequenceNode("HealthAssessment", [
            ActionNode("IdentifyPatient", self._identify_patient),
            ConditionNode("PatientIdentified", self._check_patient_identified),
            SequenceNode("HealthQuestionnaire", [
                ActionNode("AskHealthQuestion", self._ask_health_question),
                ActionNode("RecordResponse", self._record_health_response),
                ConditionNode("MoreQuestionsNeeded", self._check_more_questions)
            ]),
            ActionNode("AnalyzeSymptoms", self._analyze_symptoms),
            ActionNode("CapturePatientPhoto", self._capture_patient_photo),
            ActionNode("GenerateAssessment", self._generate_assessment),
            ActionNode("SendToDoctor", self._send_to_doctor)
        ])

    def _create_emergency_tree(self) -> BehaviorTreeNode:
        """Create behavior tree for emergency mode"""
        return SequenceNode("EmergencyMode", [
            ActionNode("StopAllMovement", self._stop_all_movement),
            ActionNode("ReturnToSafePosition", self._return_to_safe_position),
            ActionNode("AlertSystems", self._alert_systems),
            ActionNode("WaitForClearance", self._wait_for_clearance)
        ])

    # Condition check methods
    def _check_greeting_detected(self, blackboard: Dict[str, Any]) -> bool:
        """Check if greeting was detected"""
        return blackboard.get('greeting_detected', False)

    def _check_movement_time(self, blackboard: Dict[str, Any]) -> bool:
        """Check if it's time for random movement"""
        return blackboard.get('movement_time_reached', False)

    def _check_display_update_time(self, blackboard: Dict[str, Any]) -> bool:
        """Check if display needs updating"""
        return blackboard.get('display_update_time', False)

    def _check_gamepad_connected(self, blackboard: Dict[str, Any]) -> bool:
        """Check if gamepad is connected"""
        try:
            if (self.robot_controller.manual_control_module and
                hasattr(self.robot_controller.manual_control_module, 'gamepad_connected')):
                return self.robot_controller.manual_control_module.gamepad_connected
            return False
        except:
            return False

    def _check_manual_mode_active(self, blackboard: Dict[str, Any]) -> bool:
        """Check if manual mode is active"""
        try:
            if self.robot_controller.manual_control_module:
                return self.robot_controller.manual_control_module.is_manual_active()
            return False
        except:
            return False

    def _check_target_detected(self, blackboard: Dict[str, Any]) -> bool:
        """Check if follow target is detected"""
        try:
            if self.robot_controller.follow_mode_module:
                status = self.robot_controller.follow_mode_module.get_follow_status()
                return status.get('target_found', False)
            return False
        except:
            return False

    def _check_search_timeout(self, blackboard: Dict[str, Any]) -> bool:
        """Check if search timeout reached"""
        return blackboard.get('search_timeout_reached', False)

    def _check_face_detected(self, blackboard: Dict[str, Any]) -> bool:
        """Check if face is detected for registration"""
        return blackboard.get('face_detected', False)

    def _check_photo_count(self, blackboard: Dict[str, Any]) -> bool:
        """Check if enough photos captured"""
        return blackboard.get('photo_count_reached', False)

    def _check_question_received(self, blackboard: Dict[str, Any]) -> bool:
        """Check if question was received"""
        return blackboard.get('question_received', False)

    def _check_followup_needed(self, blackboard: Dict[str, Any]) -> bool:
        """Check if follow-up question needed"""
        return blackboard.get('followup_needed', False)

    def _check_patient_identified(self, blackboard: Dict[str, Any]) -> bool:
        """Check if patient was identified"""
        return blackboard.get('patient_identified', False)

    def _check_call_timeout(self, blackboard: Dict[str, Any]) -> bool:
        """Check if call timeout reached"""
        return blackboard.get('call_timeout_reached', False)

    def _check_more_questions(self, blackboard: Dict[str, Any]) -> bool:
        """Check if more health questions needed"""
        return blackboard.get('more_questions_needed', False)

    # Action methods
    def _respond_to_greeting(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Respond to detected greeting"""
        try:
            if self.robot_controller.idle_module:
                self.robot_controller.idle_module.respond_to_presence()
            blackboard['greeting_detected'] = False
            return BehaviorStatus.SUCCESS
        except:
            return BehaviorStatus.FAILURE

    def _perform_random_movement(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Perform random movement"""
        try:
            if self.robot_controller.idle_module:
                # This would trigger the idle module's random movement
                pass
            blackboard['movement_time_reached'] = False
            return BehaviorStatus.SUCCESS
        except:
            return BehaviorStatus.FAILURE

    def _update_ambient_display(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Update ambient display"""
        try:
            blackboard['display_update_time'] = False
            return BehaviorStatus.SUCCESS
        except:
            return BehaviorStatus.FAILURE

    def _idle_rest(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Idle rest action"""
        return BehaviorStatus.RUNNING

    def _process_gamepad_input(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Process gamepad input"""
        return BehaviorStatus.RUNNING

    def _monitor_emergency_stop(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Monitor for emergency stop"""
        return BehaviorStatus.RUNNING

    def _calculate_follow_movement(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Calculate follow movement"""
        return BehaviorStatus.SUCCESS

    def _execute_movement(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Execute robot movement"""
        return BehaviorStatus.SUCCESS

    def _update_camera_tracking(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Update camera tracking"""
        return BehaviorStatus.SUCCESS

    def _scan_for_target(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Scan area for target"""
        return BehaviorStatus.RUNNING

    def _exit_follow_mode(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Exit follow mode"""
        return BehaviorStatus.SUCCESS

    def _collect_patient_info(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Collect patient information"""
        return BehaviorStatus.SUCCESS

    def _capture_photo(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Capture patient photo"""
        return BehaviorStatus.SUCCESS

    def _save_patient_data(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Save patient data to database"""
        return BehaviorStatus.SUCCESS

    def _confirm_registration(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Confirm registration completion"""
        return BehaviorStatus.SUCCESS

    def _listen_for_question(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Listen for patient question"""
        return BehaviorStatus.RUNNING

    def _process_question(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Process received question"""
        return BehaviorStatus.SUCCESS

    def _deliver_answer(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Deliver answer to patient"""
        return BehaviorStatus.SUCCESS

    def _get_patients_needing_medicine(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Get list of patients needing medicine"""
        return BehaviorStatus.SUCCESS

    def _scan_for_patient(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Scan for specific patient"""
        return BehaviorStatus.RUNNING

    def _confirm_patient_identity(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Confirm patient identity"""
        return BehaviorStatus.SUCCESS

    def _check_medication(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Check patient medication"""
        return BehaviorStatus.SUCCESS

    def _dispense_medicine(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Dispense medicine to patient"""
        return BehaviorStatus.SUCCESS

    def _call_patient_name(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Call patient name"""
        return BehaviorStatus.SUCCESS

    def _move_to_next_patient(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Move to next patient"""
        return BehaviorStatus.SUCCESS

    def _identify_patient(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Identify patient for health check"""
        return BehaviorStatus.SUCCESS

    def _ask_health_question(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Ask health question"""
        return BehaviorStatus.SUCCESS

    def _record_health_response(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Record health response"""
        return BehaviorStatus.SUCCESS

    def _analyze_symptoms(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Analyze patient symptoms"""
        return BehaviorStatus.SUCCESS

    def _capture_patient_photo(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Capture patient photo for assessment"""
        return BehaviorStatus.SUCCESS

    def _generate_assessment(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Generate health assessment"""
        return BehaviorStatus.SUCCESS

    def _send_to_doctor(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Send assessment to doctor"""
        return BehaviorStatus.SUCCESS

    def _stop_all_movement(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Stop all robot movement"""
        return BehaviorStatus.SUCCESS

    def _return_to_safe_position(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Return robot to safe position"""
        return BehaviorStatus.SUCCESS

    def _alert_systems(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Alert emergency systems"""
        return BehaviorStatus.SUCCESS

    def _wait_for_clearance(self, blackboard: Dict[str, Any]) -> BehaviorStatus:
        """Wait for emergency clearance"""
        return BehaviorStatus.RUNNING

    # Main execution methods
    def set_current_tree(self, tree_name: str):
        """Set the current active behavior tree"""
        if tree_name in self.behavior_trees:
            self.current_tree = self.behavior_trees[tree_name]
            self.blackboard = {}  # Reset blackboard for new tree
            self.get_logger().info(f"Behavior tree changed to: {tree_name}")
        else:
            self.get_logger().warning(f"Unknown behavior tree: {tree_name}")

    def execute_behavior_tree(self):
        """Main behavior tree execution loop"""
        try:
            if not self.execution_active or not self.current_tree:
                return

            # Update blackboard with current robot state
            self._update_blackboard()

            # Execute current behavior tree
            status = self.current_tree.execute(self.blackboard)

            # Handle tree completion
            if status == BehaviorStatus.SUCCESS:
                self.get_logger().debug("Behavior tree completed successfully")
            elif status == BehaviorStatus.FAILURE:
                self.get_logger().debug("Behavior tree failed")

        except Exception as e:
            self.get_logger().error(f"Behavior tree execution error: {e}")

    def _update_blackboard(self):
        """Update blackboard with current robot state"""
        try:
            # Get current robot status
            if hasattr(self.robot_controller, 'get_robot_status'):
                robot_status = self.robot_controller.get_robot_status()
                self.blackboard.update(robot_status)

            # Add current time for time-based conditions
            self.blackboard['current_time'] = time.time()

        except Exception as e:
            self.get_logger().error(f"Blackboard update error: {e}")

    def start_execution(self):
        """Start behavior tree execution"""
        self.execution_active = True
        self.set_current_tree('idle')  # Start with idle tree
        self.get_logger().info("Behavior tree execution started")

    def stop_execution(self):
        """Stop behavior tree execution"""
        self.execution_active = False
        self.get_logger().info("Behavior tree execution stopped")

    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status"""
        return {
            'execution_active': self.execution_active,
            'current_tree': self.current_tree.name if self.current_tree else None,
            'available_trees': list(self.behavior_trees.keys()),
            'blackboard_size': len(self.blackboard)
        }