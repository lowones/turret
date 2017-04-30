#!/usr/bin/python
#import Adafruit_MotorHAT, Adafruit_DCMotor, Adafruit_Stepper
from Adafruit_MotorHAT import Adafruit_MotorHAT, Adafruit_DCMotor, Adafruit_StepperMotor

import time
import atexit
import RPi.GPIO as GPIO
import time

PIN=0
STATE=1
TRAN=2
MIN=3
MAX=4

index = -1  # set to -1 initially for unkown location

# create a default object, no changes to I2C address or frequency
sh = Adafruit_MotorHAT()
x_stepper = sh.getStepper(200, 1)  # 200 steps/rev, motor port #2
y_stepper = sh.getStepper(200, 2)  # 200 steps/rev, motor port #2


def main():
    markers = [[17,0,0,1,1],
               [20,0,0,225,245],
               [16,0,0,635,660],
               [12,0,0,1195,1220],
               [25,0,0,1575,1595],
               [24,0,0,1810,1810],
               [26,0,0,1,1],
               [19,0,0,45,65],
               [13,0,0,85,100],
               [6,0,0,105,120],
               [5,0,0,140,165],
               [22,0,0,300,300]
              ]
    x=[0,1,2,3,4,5]
    y=[6,7,8,9,10,11]
    GPIO.setmode(GPIO.BCM)
    atexit.register(turnOffMotors)
 
    setup_markers(x, markers)
    setup_markers(y, markers)
#    index = locate(x_stepper, x, markers)
#    sweep(x_stepper, x, markers)
#    sweep(x_stepper, x, markers, soft_min=5, soft_max=230)
#    sweep(y_stepper, y, markers, soft_max=230)
    goto_coord(990, index,  x_stepper, x, markers)
    goto_coord(20, index,  y_stepper, y, markers)

def power_supply_on():
    print("turn atx power supply on")

def power_supply_off():
    print("turn atx power supply off")

def setup_markers(axis, markers):
    print("setup markers")
    for marker in axis:
        print(marker)
        setup_gpio_input(markers[marker][PIN])

def setup_gpio_input(pin):
    print("set pin %s as an input" % pin)
    GPIO.setup(pin, GPIO.IN)

# recommended for auto-disabling motors on shutdown!
def turnOffMotors():
    for i in [1,2,3,4]:
        sh.getMotor(i).run(Adafruit_MotorHAT.RELEASE)

def step(index, motor, direction=-1):
    if direction ==  -1:
        DIR=Adafruit_MotorHAT.BACKWARD
    elif direction == 1:
        DIR=Adafruit_MotorHAT.FORWARD
    else:
        print("Invalid direction")
    motor.oneStep(DIR,  Adafruit_MotorHAT.INTERLEAVE)
    index+=direction
    return index

def marker_state(axis, markers):
    triggered_marker=-1
    count=0
    for marker in axis:
        if GPIO.input(markers[marker][PIN])==0:
            triggered_marker=marker
            count+=1
            if count > 1:
                print("Error multiple markers triggered")
    return triggered_marker

def locate(stepper, axis, markers):
    index=0
    dir=-1
    power_supply_on()
    try:
        triggered = marker_state(axis, markers)
        while triggered == -1:
            step(index, stepper, direction=dir)
            triggered = marker_state(axis, markers)
        index = markers[triggered][MAX]
        print("The located index is %s for marker %s" % (index, triggered) )
    finally:
#        GPIO.cleanup()
        power_supply_off()
    return index

def check_transition(index, dir, triggered, markers):
#    print("check if any marker has transitioned state")
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

def goto_coord(coord, index, stepper, axis, markers):
    print("Goto axis index specified")
    print("Update index to markers as triggered")
    dir=-1  # set direction to initally move toward MIN
    try:
        power_supply_on()
        if index == -1:
            index = locate(stepper, axis, markers)
        if coord > index:
            dir=1
        while index != coord:
            index = step(index, stepper, dir)
            manual_index = index
            triggered = marker_state(axis, markers)
            index = check_transition(index, dir, triggered, markers)
            gap = [manual_index, index]
            gap.sort()
            if coord in range(gap[0], gap[1]):
                index = coord
    finally:
#        GPIO.cleanup()
        power_supply_off()
    print("At index %s" % index)



def sweep(stepper, axis, markers, soft_min=-5000, soft_max=5000):
    power_supply_on()
    END_SLEEP=1.0
    MID_SLEEP=0.1
    print("sweep\n")
    index=0
    dir=-1
    print("soft_min = %s" % soft_min)
    print("soft_max = %s" % soft_max)
    time.sleep(5.0)
    print("resetting to MIN")
    mk_min=markers[axis[0]][PIN]
    while GPIO.input(mk_min)==1:
        step(index, stepper, direction=dir)
    try:
      while True:
        triggered = marker_state(axis, markers)
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
#          print "step"
          pass

#        index=index+dir
        index = step(index, stepper, direction=dir)
        print(index)
    
    finally:
      GPIO.cleanup()
      power_supply_off()


def check_ammo():
  print("Check ammo light sensor")

def fly_wheel(power_level):
  print("Set power_level of flywheel motor")

def fire_ammo():
  print("Cycle pusher servo")

if __name__ == "__main__":
  main()
