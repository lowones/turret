#!/usr/bin/python
#  
from Adafruit_MotorHAT import Adafruit_MotorHAT, Adafruit_DCMotor, Adafruit_StepperMotor

import time
import atexit
import RPi.GPIO as GPIO
import sys
import tty
import termios
from itertools import cycle

PIN=0
STATE=1
MIN=2
MAX=3

orig_setting = termios.tcgetattr(sys.stdin)

index = x_index = y_index  = -1  # set to -1 initially for unkown location

# create a default object, no changes to I2C address or frequency
sh = Adafruit_MotorHAT()
mh = Adafruit_MotorHAT(addr=0x61)
x_stepper = sh.getStepper(200, 1)  # 200 steps/rev, motor port #2
y_stepper = sh.getStepper(200, 2)  # 200 steps/rev, motor port #2
flywheel = mh.getMotor(1)
trigger = mh.getMotor(3)
atx_pin = 27

markers = [[17,0,1,1],
           [20,0,225,245],
           [16,0,635,660],
           [12,0,1195,1220],
           [25,0,1575,1595],
           [24,0,1810,1810],
           [26,0,1,1],
           [23,0,55,70],
           [13,0,90,105],
           [6,0,125,140],
           [5,0,165,185],
           [22,0,410,410]
          ]
x=[0,1,2,3,4,5]
y=[6,7,8,9,10,11]

x_min_limit = markers[x[0]][MIN]
x_max_limit = markers[x[-1]][MAX]
y_min_limit = markers[y[0]][MIN]
y_max_limit = 222

located = located_x = located_y = 0        # set located to false initially

def get_power_level(power):
    if power > 100:
        print("Power cannot be greater than 100")
        power=100
    level=int(255.0/(100.0/float(power)))
    print(level)
    return level

def test_flywheel(F, percent=60):
    power_on_delay=4.0
    print("Test flywheel")
    power_supply_on()
    power=get_power_level(percent)
    print("power level is %s" % power)
    F.setSpeed(power)
    F.run(Adafruit_MotorHAT.FORWARD)
    time.sleep(power_on_delay)
    F.run(Adafruit_MotorHAT.RELEASE)
    power_supply_off()

def shoot(F, T, percent=100, shots=1):
    power_supply_on()
#    print("shoot gun")
    trigger_power=100
#    trigger_power=255
    power_on_delay=3.0
    one_shot_time=0.15
    shot_clear_time=0.4
#    shot_duration=shots*one_shot_time
    f_power=get_power_level(percent)
    T.setSpeed(trigger_power)
    F.run(Adafruit_MotorHAT.FORWARD)
    F.setSpeed(f_power)
    time.sleep(power_on_delay)
    T.run(Adafruit_MotorHAT.FORWARD)
    s_count = 0
    while s_count < shots:
        s_count+=1
        if f_power < 249:
            f_power+=5
            F.setSpeed(f_power)
        time.sleep(one_shot_time)
    T.run(Adafruit_MotorHAT.RELEASE)
    time.sleep(shot_clear_time)
    F.run(Adafruit_MotorHAT.RELEASE)
    power_supply_off()

def main():
    atexit.register(turnOffMotors)
 
    setup_gpio(atx_pin, x, y)
#    waypoint(200, 100, 50, 0)
# COMMANDS
    menu()

def check_coord(x_c, y_c):
    if  x_c not in range(x_min_limit, x_max_limit):
        print("X coord is out of range: %s - %s" % (x_min_limit, x_max_limit))
        return False
    if  y_c not in range(y_min_limit, y_max_limit):
        print("X coord is out of range: %s - %s" % (y_min_limit, y_max_limit))
        return False
    return True

def waypoint(x_coord, y_coord, power_level, shots):
    global index
    global x_index
    global y_index
    power_supply_on()
    index = x_index
    print("goto X %s" % x_coord)
    x_index = goto_coord(x_coord, x_stepper, x)
    index = y_index
    print("goto Y %s" % y_coord)
    y_index = goto_coord(y_coord, y_stepper, y)
    shoot(flywheel, trigger, power_level, shots)
    time.sleep(2.0)
    power_supply_off()

def setup_gpio(atx, x_axis, y_axis):
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(atx, GPIO.OUT, initial=0)
    for marker in markers:
        setup_gpio_input(marker[PIN])

def power_supply_on():
    GPIO.output(atx_pin, 1)
    time.sleep(0.5)

def power_supply_off():
    GPIO.output(atx_pin, 0)

def setup_gpio_input(pin):
    print("set pin %s as an input" % pin)
    GPIO.setup(pin, GPIO.IN)

# recommended for auto-disabling motors on shutdown!
def turnOffMotors():
    global located_x
    global located_y
    for i in [1,2,3,4]:
        sh.getMotor(i).run(Adafruit_MotorHAT.RELEASE)
        mh.getMotor(i).run(Adafruit_MotorHAT.RELEASE)
    located = located_x = located_y = 0 


def step(motor, direction=-1):
#    print("step")
    global index
    if direction ==  -1:
        DIR=Adafruit_MotorHAT.BACKWARD
    elif direction == 1:
        DIR=Adafruit_MotorHAT.FORWARD
    else:
        print("Invalid direction")
    motor.oneStep(DIR,  Adafruit_MotorHAT.INTERLEAVE)
    index+=direction
    return index

def marker_state(axis):
    global located_x
    global located_y
    triggered_marker=-1
    count=0
    for marker in axis:
        if GPIO.input(markers[marker][PIN])==0:
            triggered_marker=marker
            if axis[0] == 0:
                located_x=1
            elif axis[0] == 6:
                located_y=1
            else:
                print("Error in locate, unkown axis")
            count+=1
            if count > 1:
                print("Error multiple markers triggered")
    return triggered_marker

def locate(stepper, axis):
    global index
    global located
    dir=-1
    power_supply_on()
    try:
        triggered = marker_state(axis)
        while triggered == -1:
            step(stepper, direction=dir)
            triggered = marker_state(axis)
        index = markers[triggered][MAX]
        print("The located index is %s for marker %s" % (index, triggered) )
    finally:
#        GPIO.cleanup()
#        power_supply_off()
        pass
    if located_x == 1 and located_y == 1:
        located = 1
    return index

def check_transition(dir, triggered):
    global index
    if triggered == -1:
        # check if any marker was triggered
        for marker in markers:
            if marker[STATE] == 1:
                marker[STATE] = 0
                if dir ==  1:
                    print("adjust")
                    index = marker[MIN]
                else:
                    print("adjust")
                    index = marker[MAX]
    else:
        # check if tiggered was already set
        if  markers[triggered][STATE] == 0:
            markers[triggered][STATE] = 1
            if dir ==  1:
                print("adjust")
                index = markers[triggered][MIN]
            else:
                print("adjust")
                index = markers[triggered][MAX]
    return index

def goto_coord(coord, stepper, axis):
    global index
    print("Goto axis index specified")
    print("Update index to markers as triggered")
    dir=-1  # set direction to initally move toward MIN
    try:
        if index == -1:
            index = locate(stepper, axis)
        if coord > index:
            dir=1
        while index != coord:
            index = step(stepper, dir)
            print(index)
            manual_index = index
            triggered = marker_state(axis)
            index = check_transition(dir, triggered)
            gap = [manual_index, index]
            gap.sort()
            if coord in range(gap[0], gap[1]):
                index = coord
    finally:
#        GPIO.cleanup()
#        power_supply_off()
        pass
    print("At index %s" % index)
    return index



def sweep(stepper, axis, soft_min=-5000, soft_max=5000):
    global index
    power_supply_on()
    END_SLEEP=0.1
    MID_SLEEP=0.0
    print("sweep\n")
    dir=-1
    print("soft_min = %s" % soft_min)
    print("soft_max = %s" % soft_max)
    time.sleep(3.0)
    print("resetting to MIN")
    mk_min=markers[axis[0]][PIN]
    while GPIO.input(mk_min)==1:
        step(stepper, direction=dir)
    print("starting sweep")
    try:
      while True:
        triggered = marker_state(axis)
        if triggered != -1:
            triggered = axis.index(triggered)
        if triggered==0:
          print "MIN"
          dir=1
          index=0
          time.sleep(END_SLEEP)
        elif triggered==5:
          print "MAX"
          dir=-1
          time.sleep(END_SLEEP)
        elif index > soft_max:
          print "soft MAX limit"
          dir=-1
          time.sleep(END_SLEEP)
        elif index < soft_min:
          print "soft MIN limit"
          dir=1
          time.sleep(END_SLEEP)
        elif triggered==1:
          print "mk-1"
          time.sleep(MID_SLEEP)
        elif triggered==2:
          print "mk-2"
          time.sleep(MID_SLEEP)
        elif triggered==3:
          print "mk-3"
          time.sleep(MID_SLEEP)
        elif triggered==4:
          print "mk-4"
          time.sleep(MID_SLEEP)
        else:
          pass

        index = step(stepper, direction=dir)
        print(index)
    
    finally:
#      GPIO.cleanup()
      power_supply_off()

def one():
  print("1")

def two():
  print("2")

def three():
  print("3")

def menu():
    while True:
        var = raw_input("\n\rCOMMAND: ")
        if var.startswith( 'one' ):
            one()
        elif var.startswith( 'two' ):
            input = var.split()
            input.pop(0)
            for i in input:
                 try:
                    if int(i) in range(0,101):
                        print("good value")
                    else:
                        print("out of range")
                 except ValueError:
                     print("Not int")
                 print(i)
                 print type(i)
            two()
        elif var.startswith( 'manual' ):
            manual()
        elif var.startswith( 'control' ):
            status = control()
            restart = status[0]
            while restart == 1:
                power = status[1]
                steps = status[2]
                rounds = status[3]
                status = control(power, steps, rounds, help_msg=0)
                restart = status[0]
        elif var.startswith( 'quit' ):
            power_supply_off()
            GPIO.cleanup()
            quit()
        else:
            three()

def control(power=40, steps=3, rounds=2, help_msg=1):
  global orig_setting
  bullets = [1,2,3,4,5,6]
  ammo = cycle(bullets)
  power_supply_on()
  if  help_msg == 1:
        print("control mode\r")
        print_controls()
        orig_setting = termios.tcgetattr(sys.stdin)
#  orig_setting = termios.tcgetattr(sys.stdin)
  tty.setraw(sys.stdin)
  key = 0
  while key != chr(27): # ESC
    settings_updated=0
    key=sys.stdin.read(1)[0]
    if key == 'a':
      manual_move(steps, 1, x_stepper, x) # LEFT
    elif key == 'd':
      manual_move(steps, -1, x_stepper, x) # RIGHT
    elif key == 'w':
      manual_move(steps, 1, y_stepper, y) # UP
    elif key == 'x':
      manual_move(steps, -1, y_stepper, y) # DOWN
    elif key == 's':
      manual_shoot(power, rounds)
      status = [1, power, steps, rounds]
      return status
    elif key == '?':
      print_controls()
    elif key == 'r':
      rounds =  ammo.next()
      settings_updated=1
    elif key == '+':
      if power < 100:
        power +=5
        settings_updated=1
    elif key == '-':
      if power > 0:
        power -=5
        settings_updated=1
    elif key == '[':
      if steps > 1:
        steps /=2
        settings_updated=1
    elif key == ']':
      if steps < 100:
        steps *=2
        settings_updated=1
    else:
      print("You pressed %s\r" % key)

    if steps < 1:
        steps=1
    if settings_updated == 1:
        print_settings(power, rounds, steps)

  power_supply_off()
  termios.tcsetattr(sys.stdin, termios.TCSADRAIN, orig_setting)
  status = [0, power, steps, rounds]
  return status

def print_settings(power, rounds, steps):
    print("Power Level = %s\tShoots = %s\tSteps = %s\r" % (power, rounds, steps) )

def print_controls():
    print("\n\n\r\t\t\tManual Controls")
    print("\n\r\t\t\t\tw = UP")
    print("\n\r\t\ta = LEFT        s = SHOOT        d = RIGHT")
    print("\n\r\t\t\t\tx = DOWN")
    print("\n\n\r\tr = CHANGE # SHOTS\t- = REDUCE POWER\t+ = INCREASE POWER")
    print("\n\n\r\t? = HELP \t\t[ = REDUCE STEPS\t] = INCREASE STEPS")
    print("\r")

def manual_move(steps, direction, stepper, axis):
    count = 0
    while count < steps:
        triggered = marker_state(axis)
        index = check_transition(direction, triggered)
        if check_limit(triggered, direction, axis):
            count+=1
            continue
        index = step(stepper, direction)
        count+=1

def check_limit(triggered, direction, axis):
        if triggered > -1:
            t = axis.index(triggered)
            if t == 0 and  direction ==  -1:
                print("At MIN\r")
                return True
            elif t == 5 and direction == 1:
                print("At MAX\r")
                return True
        return False

def manual_shoot(power_level, rounds):
#    print("shoot")
    sys.stdout.write('shoot')
    shoot(flywheel, trigger, power_level, rounds)
    sys.stdout.flush()
    termios.tcflush(sys.stdin, termios.TCIOFLUSH)
    print("\tCLEAR\r")

def manual():
    pass

if __name__=='__main__':
        main()


def check_ammo():
  print("Check ammo light sensor")

def fly_wheel(power_level):
  print("Set power_level of flywheel motor")

def fire_ammo():
  print("Cycle pusher servo")

if __name__ == "__main__":
  main()
