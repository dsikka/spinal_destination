#include <Wire.h>
#include <Adafruit_MotorShield.h>

Adafruit_MotorShield AFMS = Adafruit_MotorShield(); 
Adafruit_DCMotor *myMotor = AFMS.getMotor(4);

int analogPin = A3;
int val = 0; // current reading
int pval = 0; // previous reading
int ppval = 0; // previous previous reading
int avgval = 0; // average reading

int setspeed = 255;
uint8_t i; // for counter 
bool flag = true;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  AFMS.begin();  // create with the default frequency 1.6KHz
  //AFMS.begin(1000);  // OR with a different frequency, say 1KHz
  
  // Set the speed to start, from 0 (off) to 255 (max speed)
  myMotor->setSpeed(setspeed);
}

void loop() {

  val = analogRead(analogPin);
  avgval = (val + pval + ppval)/3;
  Serial.println(avgval);
  if (flag) {
    myMotor->run(BACKWARD);
    if (avgval >= 1020) {
      flag = false;
    }
    
  } else{
    myMotor->run(FORWARD);
    if (avgval <= 4) {
      flag = true;
    }
  }
  
  delay(10);
    
  myMotor->run(RELEASE);
  ppval = pval;
  pval = val;
  
}
