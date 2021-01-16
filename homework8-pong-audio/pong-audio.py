"""
    Based on: https://gist.github.com/xjcl/8ce64008710128f3a076
    Modified by PedroLopes and ShanYuanTeng for Intro to HCI class but credit remains with author

    HOW TO SETUP:
    Start the python game: >python3 pong-audio.py

    HOW TO PLAY: 
    Well.. use your auditory interface. 
    p.s.: Player 1 controls the left paddle: UP (W) DOWN (S) <- change this to auditory interface
          Player 2controls the right paddle: UP (O) DOWN (L)
    
    HOW TO QUIT: 
    Say "quit". 
    
    HOW TO INSTALL:
    Follow class wiki. 
    p.s.: this needs 10x10 image in the same directory: "white_square.png".
"""
#native imports and other imports
import math
import random
import pyglet
import sys
from playsound import playsound
import time
from pydub import AudioSegment
from pydub.playback import play
import simpleaudio as sa
from gtts import gTTS
import statistics
# speech recognition library
# -------------------------------------#
# threading so that listenting to speech would not block the whole program
import threading
# speech recognition (default using google, requiring internet)
import speech_recognition as sr
# -------------------------------------#

# pitch & volume detection
# -------------------------------------#
import aubio
import numpy as num
import pyaudio
import wave
# -------------------------------------#

#define global variables
quit = False
up = False
down = False
move = True
last_pos = 225
old_y = 0
curr_y = 0
old_x = 0
curr_x = 0
score_flag = 0
error = 0
round_flag = 0
debug = 1
restart_flag = 0
direction_y = 0
direction_x = 0
p_list=[]
list_flag=0
counter = 0

# pitch & volume detection
# -------------------------------------#
# PyAudio object.
p = pyaudio.PyAudio()
# Open stream.
stream = p.open(format=pyaudio.paFloat32,
    channels=1, rate=44100, input=True,
    frames_per_buffer=1024)
# Aubio's pitch detection.
pDetection = aubio.pitch("default", 2048,
    2048//2, 44100)
# Set unit.
pDetection.set_unit("Hz")
pDetection.set_silence(-40)
# -------------------------------------#

# keeping score of points:
p1_score = 0
p2_score = 0

#play some fun sounds?
def hit():
    playsound('hit.wav', False)
def up_bounce():
    playsound('up_bounce.mp3', False)
def down_bounce():
    playsound('down_bounce.mp3', False)

#define a function that could read out the game status
def speak(text, boolean):
    tts = gTTS(text=text, lang="en")
    filename = "voice.mp3"
    tts.save(filename)
    playsound(filename, boolean)

speak("Game Start! Score 5 points to win the game!", False)

# speech recognition functions using google api
# -------------------------------------#
def listen_to_speech():
    global quit,restart_flag,move,up,down
    while not quit:
        #input()
        print("[speech recognition] Say something!")
        # obtain audio from the microphone
        r = sr.Recognizer()
        with sr.Microphone() as source:
            audio = r.listen(source, phrase_time_limit=1.5)
        # recognize speech using Google Speech Recognition
        try:
            # for testing purposes, we're just using the default API key
            # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
            # instead of `r.recognize_google(audio)`
            recog_results = r.recognize_google(audio)
            print("[speech recognition] Google Speech Recognition thinks you said \"" + recog_results + "\"")
            # if recognizing quit and exit then exit the program
            if "quit" in recog_results or "exit" in recog_results or "restart" in recog_results:
                quit = True

        except sr.UnknownValueError:
            print("[speech recognition] Google Speech Recognition could not understand audio")
        except sr.RequestError as e:
            print("[speech recognition] Could not request results from Google Speech Recognition service; {0}".format(e))
    

# -------------------------------------#
# pitch & volume detection
# -------------------------------------#
def sense_microphone():
    global quit,move,up,down
    while not quit:
        data = stream.read(1024,exception_on_overflow=False)
        samples = num.frombuffer(data,
            dtype=aubio.float_type)
        # Compute the pitch of the microphone input
        pitch = pDetection(samples)[0]
# -------------------------------------#
#learn the code from this website: https://simpleaudio.readthedocs.io/en/latest/simpleaudio.html
def make_sound(i):
    freq = i #in units of Hz
    fs = 44100  #44100 samples every second by convention
    sec = 0.6  #duration of the sound
    #create an array with seconds*sample_rate steps
    t = num.linspace(0, sec, sec * fs, False)
    #create sine wave
    note = num.sin(freq * t * 2 * num.pi)
    #check thins are in 16-bit range
    audio = note * (2**15 - 1) / num.max(num.abs(note))
    #convert to 16-bit data
    audio = audio.astype(num.int16)
    #play sound
    play_obj = sa.play_buffer(audio, 1, 2, fs)

class Ball(object):

    def __init__(self):
        self.debug = 0
        self.TO_SIDE = 5
        self.x = 50.0 + self.TO_SIDE
        self.y = float( random.randint(0, 450) )
        self.x_old = self.x  # coordinates in the last frame
        self.y_old = self.y
        self.vec_x = 2**0.5 / 2  # sqrt(2)/2
        self.vec_y = random.choice([-1, 1]) * 2**0.5 / 2

class Player(object):

    def __init__(self, NUMBER, screen_WIDTH=800):
        """NUMBER must be 0 (left player) or 1 (right player)."""
        self.NUMBER = NUMBER
        self.x = 50.0 + (screen_WIDTH - 100) * NUMBER
        self.y = 50.0
        self.last_movements = [0]*4  # short movement history
                                    # used for bounce calculation
        self.up_key, self.down_key = None, None
        if NUMBER == 0:
            self.up_key = pyglet.window.key.W
            self.down_key = pyglet.window.key.S
        elif NUMBER == 1:
            self.up_key = pyglet.window.key.O
            self.down_key = pyglet.window.key.L


class Model(object):
    """Model of the entire game. Has two players and one ball."""

    def __init__(self, DIMENSIONS=(800, 450)):
        """DIMENSIONS is a tuple (WIDTH, HEIGHT) of the field."""
        # OBJECTS
        WIDTH = DIMENSIONS[0]
        self.players = [Player(0, WIDTH), Player(1, WIDTH)]
        self.ball = Ball()
        # DATA
        self.pressed_keys = set()  # set has no duplicates
        self.quit_key = pyglet.window.key.Q
        self.speed = 6  # in pixels per frame # 6 originally
        self.ball_speed = self.speed #* 2.5
        self.WIDTH, self.HEIGHT = DIMENSIONS
        # STATE VARS
        self.paused = False
        self.i = 0  # "frame count" for debug

    def reset_ball(self, who_scored):
        """Place the ball anew on the loser's side."""
        if debug: print(str(who_scored)+" scored. reset.")
        
        self.ball.y = float( random.randint(0, self.HEIGHT) )
        self.ball.vec_y = random.choice([-1, 1]) * 2**0.5 / 2
        if who_scored == 0:
            self.ball.x = self.WIDTH - 50.0 - self.ball.TO_SIDE
            self.ball.vec_x = - 2**0.5 / 2
        elif who_scored == 1:
            self.ball.x = 50.0 + self.ball.TO_SIDE
            self.ball.vec_x = + 2**0.5 / 2
        elif who_scored == "debug":
            self.ball.x = 70  # in paddle atm -> usage: hold f
            self.ball.y = self.ball.debug
            self.ball.vec_x = -1
            self.ball.vec_y = 0
            self.ball.debug += 0.2
            if self.ball.debug > 100:
                self.ball.debug = 0
        
    def check_if_oob_top_bottom(self):
        """Called by update_ball to recalc. a ball above/below the screen."""
        # bounces. if -- bounce on top of screen. elif -- bounce on bottom.
        b = self.ball
        if b.y - b.TO_SIDE < 0:
            down_bounce() #noise indicate bounce
            #indicate game status
            ball_bounce = threading.Thread(target=speak("bounce down",False), args=())
            ball_bounce.start()
            illegal_movement = 0 - (b.y - b.TO_SIDE)
            b.y = 0 + b.TO_SIDE + illegal_movement
            b.vec_y *= -1
        elif b.y + b.TO_SIDE > self.HEIGHT:
            up_bounce() #noise indicate bounce
            #indicate game status
            ball_bounce = threading.Thread(target=speak("bounce up",False), args=())
            ball_bounce.start()
            illegal_movement = self.HEIGHT - (b.y + b.TO_SIDE)
            b.y = self.HEIGHT - b.TO_SIDE + illegal_movement
            b.vec_y *= -1

    def check_if_oob_sides(self):
        global p2_score, p1_score
        """Called by update_ball to reset a ball left/right of the screen."""
        b = self.ball
        if b.x + b.TO_SIDE < 0:  # leave on left
            self.reset_ball(1)
            p2_score+=1
            speak("Goal"+str(p1_score)+"to"+str(p2_score),True)

        elif b.x - b.TO_SIDE > self.WIDTH:  # leave on right
            p1_score+=1
            self.reset_ball(0)
            speak("Goal"+str(p1_score)+"to"+str(p2_score),True)

    def check_if_paddled(self): 
        """Called by update_ball to recalc. a ball hit with a player paddle."""
        global round_flag, error
        b = self.ball
        p0, p1 = self.players[0], self.players[1]
        angle = math.acos(b.vec_y)  
        factor = random.randint(5, 15)  
        cross0 = (b.x < p0.x + 2*b.TO_SIDE) and (b.x_old >= p0.x + 2*b.TO_SIDE)
        cross1 = (b.x > p1.x - 2*b.TO_SIDE) and (b.x_old <= p1.x - 2*b.TO_SIDE)
        if cross0 and -25 < b.y - p0.y < 25:
            if round_flag == 0:
                error = random.choice([-30,0,30])
                round_flag =1
            elif round_flag == 1:
                error = random.choice([-30,0,30])
                round_flag =0
            #playhit = threading.Thread(target=hit(), args=())
            #playhit.start()
            hit()
            speak("Player 1 Hit!", False)
            if debug: print("hit at "+str(self.i))
            illegal_movement = p0.x + 2*b.TO_SIDE - b.x
            b.x = p0.x + 2*b.TO_SIDE + illegal_movement
            angle -= sum(p0.last_movements) / factor / self.ball_speed
            b.vec_y = math.cos(angle)
            b.vec_x = (1**2 - b.vec_y**2) ** 0.5
        elif cross1 and -25 < b.y - p1.y < 25:
            #playhit = threading.Thread(target=hit(), args=())
            #playhit.start()
            if round_flag == 0:
                error = random.choice([-30,0,30])
                round_flag =1
            elif round_flag == 1:
                error = random.choice([-30,0,30])
                round_flag =0
            hit()
            speak("Player 2 Hit!", False)
            if debug: print("hit at "+str(self.i))
            illegal_movement = p1.x - 2*b.TO_SIDE - b.x
            b.x = p1.x - 2*b.TO_SIDE + illegal_movement
            angle -= sum(p1.last_movements) / factor / self.ball_speed
            b.vec_y = math.cos(angle)
            b.vec_x = - (1**2 - b.vec_y**2) ** 0.5


# -------------- Ball position: you can find it here -------
    def update_ball(self):
        global score_flag,old_y, curr_y, direction_y,old_x, curr_x, direction_x
        """
            Update ball position with post-collision detection.
            I.e. Let the ball move out of bounds and calculate
            where it should have been within bounds.

            When bouncing off a paddle, take player velocity into
            consideration as well. Add a small factor of random too.
        """
        self.i += 1  # "debug"
        b = self.ball     
        b.x_old, b.y_old = b.x, b.y
        old_y = b.y #record old y
        old_x = b.x #record old x 
        b.x += b.vec_x * self.ball_speed 
        b.y += b.vec_y * self.ball_speed
        

        curr_y = b.y #record new y
        curr_x = b.x #record new x
        
        #detect whether the ball is going up or down
        if curr_y-old_y>0:
            #down
            direction_y = 0
        else:
            #up
            direction_y = 1

        #detect whether the ball is going right or left
        if curr_x-old_x>0:
            #right
            direction_x = 0
        else:
            #left
            direction_x = 1

        # if 75 >b.x and b.x> 71:
        #     make_sound(100)
        #make sound to indicate the ball position
        if direction_x == 1 and b.x < 500 and b.x> 100:
            if b.y >= 5.5 and b.y < 9.5:
                make_sound(140) 
            elif b.y >= 35.5 and b.y < 39.5:
                make_sound(170) 
            elif b.y >= 65.5 and b.y < 69.5:
                make_sound(200)
            elif b.y >= 95.5 and b.y < 99.5:
                make_sound(230)
            elif b.y >= 125.5 and b.y < 129.5:
                make_sound(260)
            elif b.y >= 155.5 and b.y < 159.5:
                make_sound(290)
            elif b.y >= 185.5 and b.y < 189.5:
                make_sound(320)
            elif b.y >= 215.5 and b.y < 219.5:
                make_sound(350)
            elif b.y >= 245.5 and b.y < 249.5:
                make_sound(380)
            elif b.y >= 275.5 and b.y < 279.5:
                make_sound(410)
            elif b.y >= 305.5 and b.y < 309.5:
                make_sound(440)
            elif b.y >= 335.5 and b.y < 339.5:
                make_sound(470)
            elif b.y >= 365.5 and b.y < 369.5:
                make_sound(500)
            elif b.y >= 395.5 and b.y < 399.5:
                make_sound(530)
            elif b.y >= 425.5 and b.y < 429.5:
                make_sound(560)
        
        self.check_if_oob_top_bottom()  # oob: out of bounds
        self.check_if_oob_sides()
        self.check_if_paddled()

        #indicate status of the game
        if score_flag ==1:
            speak ("Player 1 won!", True)
            speak ("Quit and restart a new game!", True)
            speech_thread = threading.Thread(target=listen_to_speech, args=())
            speech_thread.start()
            
        elif score_flag ==2:
            speak ("Player 2 won!", True)
            speak ("Quit and restart a new game!", True)
            speech_thread = threading.Thread(target=listen_to_speech, args=())
            speech_thread.start()
            
        #indicate status of the game
        if p1_score >=5:
            score_flag=1
        elif p2_score >=5:
            score_flag=2


    def update(self):
        """Work through all pressed keys, update and call update_ball."""
        global quit,error,last_pos,move,up,down,direction_y,p_list,list_flag,counter
        pks = self.pressed_keys
        if quit:
            sys.exit(1)
        if self.quit_key in pks:
            exit(0)
        if pyglet.window.key.R in pks and debug:
            self.reset_ball(1)
        if pyglet.window.key.F in pks and debug:
            self.reset_ball("debug")

        # -------------- If you want to change paddle position, change it here
        # player 1: the user controls the left player by W/S but you should change it to VOICE input
        p1 = self.players[0]
        p1.last_movements.pop(0)
        b = self.ball
        
        data = stream.read(1024,exception_on_overflow=False)
        samples = num.frombuffer(data, dtype=aubio.float_type)
        pitch = pDetection(samples)[0] #use the pitch to control
        #print("pitch",pitch)  

        if direction_y ==0:
            #down
            if pitch !=0 and list_flag == 0:
                #init list_flag
                list_flag = 1
                p1.last_movements.append(0)
                counter+=1
                #we don't append the first pitch

            elif counter == 3 and list_flag == 1:
            
                clean_list = [x for x in p_list if x < 900]
                if clean_list:
                    move = statistics.median(clean_list)
                    #print ("down move")
                    if move == 0:
                        # remain at the last position
                        p1.y = last_pos 
                        p1.last_movements.append(last_pos)
                    else:
                        if move<140-60:
                            p1.y = 15
                            last_pos = 15
                            p1.last_movements.append(15)
                        elif move>560-60:
                            p1.y = 435
                            last_pos = 435
                            p1.last_movements.append(435)
                        else:
                            p1.y = move-125+60 #prediction 
                            last_pos = move-125+60 #prediction 
                            p1.last_movements.append(move-125+60)
                
                list_flag = 0
                p_list = []
                counter = 0
                
            elif pitch !=0 and list_flag == 1:
                counter+=1
                p_list.append(pitch)
                #last_pit = pitch
                p1.last_movements.append(pitch)
                #print ("counter", counter)
            else:
                p1.y = last_pos 
                #last_pit = pitch
                p1.last_movements.append(last_pos)
        else:
            #up
            if pitch !=0 and list_flag == 0:
                #init list_flag
                list_flag = 1
                p1.last_movements.append(0)
                counter+=1
                #we don't append the first pitch

            elif counter == 3 and list_flag == 1:
            
                clean_list = [x for x in p_list if x < 900]
                if clean_list:
                    move = statistics.median(clean_list)
                    #print ("up move")
                    if move == 0:
                        p1.y = last_pos 
                        p1.last_movements.append(last_pos)
                    else:
                        if move<140+60:
                            p1.y = 15
                            last_pos = 15
                            p1.last_movements.append(15)
                        elif move>560+60:
                            p1.y = 435
                            last_pos = 435
                            p1.last_movements.append(435)
                        else:
                            p1.y = move-125-60 #prediction 
                            last_pos = move-125-60 #prediction 
                            p1.last_movements.append(move-125-60)

                list_flag = 0
                p_list = []
                counter = 0

            elif pitch !=0 and list_flag == 1:
                counter+=1
                p_list.append(pitch)
                #last_pit = pitch
                p1.last_movements.append(pitch)
                #print ("counter", counter)
            
            else:
                p1.y = last_pos 
                #last_pit = pitch
                p1.last_movements.append(last_pos) 

        if up == True: #change this to voice input, which goes up
            if p1.y < 12.5:
                up = False
            else:
                p1.y -= self.speed+25
                p1.last_movements.append(-self.speed+25)
                up = False
        elif down == True: #change this to voice input, which goes down
            if p1.y > 437.5:
                down = False
            else:
                p1.y += self.speed+25
                p1.last_movements.append(+self.speed+25)
                down = False
        
        else:
            # notice how we popped from _place_ zero,
            # but append _a number_ zero here. it's not the same.
            p1.last_movements.append(0)
        
        if direction_x == 1 and b.x < 80 and b.x > 76:
            
            if b.y+15 > p1.y+60 and p1.y+60 > b.y-15:
                #print ("adjust down 60!")
                if p1.y+60> 560:
                    p1.y = 435
                    last_pos = 435
                    p1.last_movements.append(435)
                else:
                    p1.y += 60
                    last_pos = p1.y
                    p1.last_movements.append(p1.y) 
            elif b.y+15 > p1.y-60 and p1.y-60 > b.y-15:
                #print ("adjust up 60!")
                if p1.y-60> 140:
                    p1.y = 15
                    last_pos = 15
                    p1.last_movements.append(15)
                else:
                    p1.y -= 60
                    last_pos = p1.y
                    p1.last_movements.append(p1.y) 
            elif b.y+15 > p1.y+30 and p1.y+30 > b.y-15:
                #print ("adjust down 30!")
                if p1.y+60> 560:
                    p1.y = 435
                    last_pos = 435
                    p1.last_movements.append(435)
                else:
                    p1.y += 30
                    last_pos = p1.y
                    p1.last_movements.append(p1.y)
            elif b.y+15 > p1.y-30 and p1.y-30 > b.y-15:
                #print ("adjust up 30!")
                if p1.y-60> 140:
                    p1.y = 15
                    last_pos = 15
                    p1.last_movements.append(15)
                else:
                    p1.y -= 30
                    last_pos = p1.y
                    p1.last_movements.append(p1.y) 
        # ----------------- DO NOT CHANGE BELOW ----------------
        # player 2: the other user controls the right player by O/L
        p2 = self.players[1]
        p2.last_movements.pop(0)
        if p2.up_key in pks and p2.down_key not in pks: #change this to voice input
            p2.y -= self.speed
            p2.last_movements.append(-self.speed)
        elif p2.up_key not in pks and p2.down_key in pks: #change this to voice input
            p2.y += self.speed
            p2.last_movements.append(+self.speed)
        else:
            b = self.ball
            temp = b.y+error #I made a simple opponet that has random chances to make mistakes
            p2.y = temp
            p2.last_movements.append(temp)
            if temp < 15:
                p2.y = 15
                p2.last_movements.append(15)
            elif temp > 435:
                p2.y = 435
                p2.last_movements.append(435)
            # notice how we popped from _place_ zero,
            # but append _a number_ zero here. it's not the same.
            #p2.last_movements.append(0)

        self.update_ball()
        label.text = str(p1_score)+':'+str(p2_score)

class Controller(object):

    def __init__(self, model):
        self.m = model

    def on_key_press(self, symbol, modifiers):
        # `a |= b`: mathematical or. add to set a if in set a or b.
        # equivalent to `a = a | b`.
        # XXX p0 holds down both keys => p1 controls break  # PYGLET!? D:
        self.m.pressed_keys |= set([symbol])

    def on_key_release(self, symbol, modifiers):
        if symbol in self.m.pressed_keys:
            self.m.pressed_keys.remove(symbol)

    def update(self):
        self.m.update()


class View(object):

    def __init__(self, window, model):
        self.w = window
        self.m = model
        # ------------------ IMAGES --------------------#
        # "white_square.png" is a 10x10 white image
        lplayer = pyglet.resource.image("white_square.png")
        self.player_spr = pyglet.sprite.Sprite(lplayer)

    def redraw(self):
        # ------------------ PLAYERS --------------------#
        TO_SIDE = self.m.ball.TO_SIDE
        for p in self.m.players:
            self.player_spr.x = p.x//1 - TO_SIDE
            # oh god! pyglet's (0, 0) is bottom right! madness.
            self.player_spr.y = self.w.height - (p.y//1 + TO_SIDE)
            self.player_spr.draw()  # these 3 lines: pretend-paddle
            self.player_spr.y -= 2*TO_SIDE; self.player_spr.draw()
            self.player_spr.y += 4*TO_SIDE; self.player_spr.draw()
        # ------------------ BALL --------------------#
        self.player_spr.x = self.m.ball.x//1 - TO_SIDE
        self.player_spr.y = self.w.height - (self.m.ball.y//1 + TO_SIDE)
        self.player_spr.draw()


class Window(pyglet.window.Window):

    def __init__(self, *args, **kwargs):
        DIM = (800, 450)  # DIMENSIONS
        super(Window, self).__init__(width=DIM[0], height=DIM[1],
                                     *args, **kwargs)
        # ------------------ MVC --------------------#
        the_window = self
        self.model = Model(DIM)
        self.view = View(the_window, self.model)
        self.controller = Controller(self.model)
        # ------------------ CLOCK --------------------#
        fps = 30.0
        pyglet.clock.schedule_interval(self.update, 1.0/fps)
        #pyglet.clock.set_fps_limit(fps)

    def on_key_release(self, symbol, modifiers):
        self.controller.on_key_release(symbol, modifiers)

    def on_key_press(self, symbol, modifiers):
        self.controller.on_key_press(symbol, modifiers)

    def update(self, *args, **kwargs):
        # XXX make more efficient (save last position, draw black square
        # over that and the new square, don't redraw _entire_ frame.)
        self.clear()
        self.controller.update()
        self.view.redraw()


window = Window()
label = pyglet.text.Label(str(p1_score)+':'+str(p2_score),
                      font_name='Times New Roman',
                      font_size=36,
                      x=window.width//2, y=window.height//2,
                      anchor_x='center', anchor_y='center')
@window.event
def on_draw():
    #window.clear()
    label.draw()

# speech recognition thread
#-------------------------------------#
#start a thread to listen to speech
# speech_thread = threading.Thread(target=listen_to_speech, args=())
# speech_thread.start()
# -------------------------------------#

# pitch & volume detection
# -------------------------------------#
# start a thread to detect pitch and volume
# microphone_thread = threading.Thread(target=sense_microphone, args=())
# microphone_thread.start()
# -------------------------------------#

if debug: print("init window...")
if debug: print("done! init app...")
pyglet.app.run()


