from robot_interface import RobotInterface

available_functions = {
    'test_text': RobotInterface.test_text,
    'hand_action': RobotInterface.hand_action,
    'handshake': RobotInterface.handshake,
    'perform_arm_action' : RobotInterface.perform_arm_action,
    'move': RobotInterface.move
}

tool_specs = [
    {
        'type': 'function',
        'function': {
            'name': 'test_text',
            'description': 'Произнесение заготовленного текста',
            'parameters': {'type': 'object', 'properties': {}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'hand_action',
            'description': 'Действие с кистями рук, открыть или закрыть',
            'parameters': {
                'type': 'object',
                'required': ['hand', 'action'],
                'properties': 
                    {
                    'hand': {'type': 'string', 'description': 'right, left, both'},
                    'action': {'type': 'string', 'description': 'open, close'}
                    },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'perform_arm_action',
            'description': 'Выполнить жест рукой по имени действия',
            'parameters': {
                'type': 'object',
                'required': ['action_name'],
                'properties': {
                    'action_name': {
                        'type': 'string',
                        'description': (
                            'Имя действия. Допустимые значения: '
                            '"put_your_hands_down", "turn_back_wave", "two-hand_kiss", "left_kiss", "right_kiss", '
                            '"hands_up", "clap", "high_five", "hug", "heart", "right_heart", "reject", '
                            '"right_hand_up", "x-ray", "face_wave", "high_wave", "shake_hand", '
                            '"box_left_hand_win", "box_right_hand_win", "box_both_hand_win", '
                            '"extend_right_arm_forward", "right_hand_on_mouth", "right_hand_on_heart", '
                            '"both_hands_up_deviate_right", "emphasize"'
                        ),
                        'enum': [
                            "put_your_hands_down", "turn_back_wave", "two-hand_kiss", "left_kiss", "right_kiss",
                            "hands_up", "clap", "high_five", "hug", "heart", "right_heart", "reject",
                            "right_hand_up", "x-ray", "face_wave", "high_wave", "shake_hand",
                            "box_left_hand_win", "box_right_hand_win", "box_both_hand_win",
                            "extend_right_arm_forward", "right_hand_on_mouth", "right_hand_on_heart",
                            "both_hands_up_deviate_right", "emphasize"
                            ]
                        }
                    }
                }
            }
    },
    {
        'type': 'function',
        'function': {
            'name': 'handshake',
            'description': 'рукопожатие, приветствование, дай руку',
            'parameters': {'type': 'object', 'properties': {}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'move',
            'description': 'передвижение, шагать, идти',
            'parameters': {  # ← должно быть parameters, не properties
                'type': 'object',
                'required': ['vx', 'vy', 'vyaw'],
                'properties': {
                    'vx': {
                        'type': 'float',
                        'description': 'Шаг вперёд (положительное число) или Шаг назад (отрицательное число) (0.3-1)'
                    },
                    'vy': {
                        'type': 'float',
                        'description': 'Шаг влево (положительное число) или Шаг вправо (отрицательное число) (0.3-1)'
                    },
                    'vyaw': {
                        'type': 'float',
                        'description': 'Поворот: отрицательное значение — по часовой стрелке, положительное — против часовой стрелки(0.3-1)'
                    }
                    }
                }
            }
    }

]

