from distutils.command.upload import upload
import os
import sys
import time
import logging
from PyQt5.QtWidgets import (QApplication, QComboBox, QFileDialog, QLineEdit, QPushButton,
                             QStackedLayout, QRadioButton, QVBoxLayout, QHBoxLayout, QWidget, QTextEdit,
                             QLabel, QButtonGroup)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QMouseEvent
from matplotlib import pyplot as plt
import numpy as np

from handlers import CalibrationHandler
from PIL import Image
from PIL.ImageQt import ImageQt
import cv2 



sys.path.append('D:\\Basketball\\VertMeasure')

class Window(QWidget):
    def __init__(self, screen_width, screen_height):
        super().__init__()
        self.setup_logger()
        self.ch = None
        self.__calibration_qImg = None

        #DEV STUFF
        self.toggle = True
        self.shoulder_offset = 0
        self.rim_offset = 0
        self.ground_offset = 0
        self.frame_offset = 0

        self.mouse_state = 0

        self.border_offset = 12
        self.measured_jump_height = -1
        self.cal_tl, self.cat_br = (0, 11), (1897, 1068)

        #Timers
        self.frame_rate_demo = 15
        self.demo_timer = None

        #General Application Setup
        self.reset_program = 0
        self.app_start_time = time.time()
        self.setWindowTitle("Analisador de Saltos")
        self.windowHeight, self.windowWidth = screen_height, screen_width
        self.setFixedSize(self.windowWidth, self.windowHeight)
        
        #Page Layout Setup
        self.general_layout = QVBoxLayout()
        self.setLayout(self.general_layout)
        self.stackedLayout = QStackedLayout()
        self.entrance = self.entrance_page_generator()
        self.config_p = self.config_page_generator()
        self.cal_scale = None
        self.export_p = None
        self.demo = None
        
        self.stackedLayout.addWidget(self.entrance)
        self.stackedLayout.addWidget(self.config_p)
        
        self.general_layout.addLayout(self.stackedLayout)
        print(f"Stacked Layout Count: {self.stackedLayout.count()}")

        self.showFullScreen()

    '''----- Program Infrastructure ----- '''

    def setup_logger(self):
        self.log = logging.getLogger('VertMeasure')
        self.log.setLevel(logging.DEBUG)
        # create file handler which logs even debug messages
        fh = logging.FileHandler('run.log', mode="w")
        fh.setLevel(logging.DEBUG)
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        # add the handlers to the logger
        self.log.addHandler(fh)
        self.log.addHandler(ch)

    def keyPressEvent(self, e):
        #Closes the application on the window event e
        if e.key() == Qt.Key_Escape:
            self.log.info("Exiting Program Via: Escape Key")
            self.close()
    
    def next_page(self):
        if self.reset_program:
            self.reset_program = 0
            self.stackedLayout.removeWidget(self.cal_scale)
            self.stackedLayout.removeWidget(self.export_p)
            self.stackedLayout.removeWidget(self.demo)
            self.ch = None
            self.stackedLayout.setCurrentIndex(1)
            return

        self.stackedLayout.setCurrentIndex(self.stackedLayout.currentIndex() + 1)
        self.log.info(f"Now Switching Pages from {self.stackedLayout.currentIndex()} to {self.stackedLayout.currentIndex() + 1}")
    
    def reset_page(self):
        self.reset_program = 1
        self.next_page()

    '''----- Output Formatting -----'''
    def export_jump_info(self, output_path, name_base):
        self.ch.export_jump_info(output_path, name_base)
        self.export_button_label.setText("Information successfully exported to the output folder")
        self.export_button_label.update()
        plt.savefig(f'{output_path}\\{name_base}_graph.png')


    '''----- UI Definitions ------'''

    def entrance_page_generator(self):
        entrance_page = QWidget()
        
        entrance_layout = QVBoxLayout()
        self.entrance_label = QLabel("Analisador de Saltos")
        self.entrance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.begin_button = QPushButton("Inicio", clicked=self.next_page)
        entrance_layout.addWidget(self.entrance_label)
        entrance_layout.addWidget(self.begin_button)
        entrance_page.setLayout(entrance_layout)

        return entrance_page

    def config_page_generator(self):
            config_page = QWidget()
            config_layout = QVBoxLayout()
            button_layout = QHBoxLayout()
        

            style_group = QButtonGroup(config_page)
            vid_group = QButtonGroup(config_page)
            ###Entry Definitions

            # Video Source: Widget declaration --------------------------------------------
            upload_entry = QHBoxLayout()
            upload_label = QLabel("Caminho:")
            self.upload_line = QLineEdit()
            upload_button = QPushButton("Upload", clicked=self.get_video_file)
            # Widget Specifications
            self.upload_line.setMinimumWidth(int(self.windowWidth * 0.6))

            self.upload_line.setReadOnly(1)
            upload_button.setMinimumWidth(int(self.windowWidth * 0.2))

            # Layout
            upload_entry.addWidget(upload_label)
            upload_entry.addStretch(1)
            upload_entry.addWidget(self.upload_line)
            upload_entry.addStretch(1)
            upload_entry.addWidget(upload_button)

            # Name: Widget declaration ----------------------------------------------------
            name_entry = QHBoxLayout()
            name_label = QLabel("Nome:")
            self.name_line = QLineEdit()
            # Widget Specifications
            self.name_line.setMinimumWidth(int(self.windowWidth * 0.9))

            # Layout
            name_entry.addWidget(name_label)
            name_entry.addStretch(1)
            name_entry.addWidget(self.name_line)

            # Height: Widget declaration --------------------------------------------------
            height_entry = QHBoxLayout()
            height_label = QLabel("Altura (Polegadas):")
            self.height_line = QLineEdit()
            # Widget Specifications
            self.height_line.setMinimumWidth(int(self.windowWidth * 0.8))
            # Layout
            height_entry.addWidget(height_label)
            height_entry.addStretch(1)
            height_entry.addWidget(self.height_line)

            # Jump Style: Widget declaration -------------------------------------------------
            style_entry = QHBoxLayout()
            style_label = QLabel("Ponde de Referencia:")
            self.style_ground = QRadioButton("Solo")
            self.style_rim = QRadioButton("Cravicula")
            style_group.addButton(self.style_ground)
            style_group.addButton(self.style_rim)
            self.style_rim.setChecked(1)
            # Widget Specifications
            self.style_ground.setMinimumWidth(int(self.windowWidth * 0.1))
            self.style_rim.setMinimumWidth(int(self.windowWidth * 0.1))
            # Layout
            style_entry.addWidget(style_label)
            style_entry.addStretch(1)
            style_entry.addWidget(self.style_ground)
            style_entry.addWidget(self.style_rim)
            style_entry.addStretch(5)

            # Video Format: Widget declaration -------------------------------------------------
            vid_entry = QHBoxLayout()
            vid_label = QLabel("Formato de video:")
            self.vid_vert = QRadioButton("Vertical")
            self.vid_landscape = QRadioButton("Horizontal")
            vid_group.addButton(self.vid_vert)
            vid_group.addButton(self.vid_landscape)
            
            self.vid_vert.setChecked(1)
            # Widget Specifications
            self.vid_vert.setMinimumWidth(int(self.windowWidth * 0.1))
            self.vid_landscape.setMinimumWidth(int(self.windowWidth * 0.1))
            # Layout
            vid_entry.addWidget(vid_label)
            vid_entry.addStretch(1)
            vid_entry.addWidget(self.vid_vert)
            vid_entry.addWidget(self.vid_landscape)
            vid_entry.addStretch(5)

            #Button Definitions
            self.config_set_msg = QLabel("")
            self.config_set_button = QPushButton("Confirmar", clicked=self.confirm_config)
            self.config_set_button.setFixedWidth(int(self.windowWidth / 5))
            
            button_layout.addWidget(self.config_set_msg)
            button_layout.addWidget(self.config_set_button, alignment=Qt.AlignmentFlag.AlignRight)
            config_layout.addStretch(2)
            config_layout.addLayout(upload_entry)
            config_layout.addStretch(1)
            config_layout.addLayout(name_entry)
            config_layout.addStretch(1)
            config_layout.addLayout(height_entry)
            config_layout.addStretch(1)
            config_layout.addLayout(style_entry)
            config_layout.addStretch(1)
            config_layout.addLayout(vid_entry)
            config_layout.addStretch(6)
            config_layout.addLayout(button_layout)
            config_page.setLayout(config_layout)

            return config_page

    def calibration_page_generator(self, ref_style=0):
        calibration_page = QWidget()
        calibration_layout = QVBoxLayout()
        button_layout = QHBoxLayout()


        self.calibration_label = QLabel(self)
            #self.calibration_label = QLabel(str(self.shoulder_offset))
        self.calibration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.confirm_offset_btn = QPushButton("Confirmar", clicked=self.confirm_offset)

        if ref_style == 1:
            rim_button_layout = QVBoxLayout()
            ground_button_layout = QVBoxLayout()
            frame_button_layout = QVBoxLayout()
            self.add_rim_offset_btn = QPushButton("Aumentar referencia", clicked=self.increase_rim_offset)
            self.sub_rim_offset_btn = QPushButton("Diminuir referencia", clicked=self.decrease_rim_offset)
            self.add_ground_offset_btn = QPushButton("Aumentar chao", clicked=self.increase_ground_offset)
            self.sub_ground_offset_btn = QPushButton("Diminuir chao", clicked=self.decrease_ground_offset)
            self.frame_next_btn = QPushButton("Proximo Frame", clicked=self.rim_frame_forward)
            self.frame_prev_btn = QPushButton("Frame anterior", clicked=self.rim_frame_back)
            rim_button_layout.addWidget(self.add_rim_offset_btn)
            rim_button_layout.addWidget(self.sub_rim_offset_btn)
            ground_button_layout.addWidget(self.add_ground_offset_btn)
            ground_button_layout.addWidget(self.sub_ground_offset_btn)
            frame_button_layout.addWidget(self.frame_next_btn)
            frame_button_layout.addWidget(self.frame_prev_btn)
            button_layout.addLayout(ground_button_layout)
            button_layout.addLayout(rim_button_layout)
            button_layout.addLayout(frame_button_layout)
            init_frame = self.ch.get_init_launch_frame()
        else:
            self.add_shoulder_offset_btn = QPushButton("Aumentar", clicked=self.increase_shoulder_offset)
            self.sub_shoulder_offset_btn = QPushButton("Diminuir", clicked=self.decrease_shoulder_offset)
            button_layout.addWidget(self.add_shoulder_offset_btn)
            button_layout.addWidget(self.sub_shoulder_offset_btn)
            init_frame = self.ch.get_init_head_frame()
        
        button_layout.addWidget(self.confirm_offset_btn)
        calibration_layout.addWidget(self.calibration_label)
        calibration_layout.addLayout(button_layout)
        calibration_page.setLayout(calibration_layout)
            
            #Loading the loading calibration image
            

        frame_img = Image.fromarray(init_frame)
        self.__calibration_qImg = ImageQt(frame_img)
        self.kin_pixmap = QPixmap.fromImage(self.__calibration_qImg)
        self.calibration_label.setPixmap(self.kin_pixmap)
        

        return calibration_page
    
    def export_page_generator(self):
        export_page = QWidget()
        export_layout = QVBoxLayout()
        button_layout = QVBoxLayout()
        button_layout_row_a = QHBoxLayout()
        button_layout_row_b = QHBoxLayout()

        self.export_label = QLabel(text=f"Pulo Vertical: {self.measured_jump_height:.2f} inches")
        self.export_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.demo_btn = QPushButton("Demonstração", clicked=self.setup_demo_page)
        self.export_btn = QPushButton("Graficos", clicked=self.export_jump_info)
        self.export_exit_button = QPushButton("Sair", clicked=self.close)
        self.export_reset_button = QPushButton("Novo Pulo", clicked=self.reset_page)
        self.export_button_label = QLabel("")
        self.export_button_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        button_layout_row_a.addWidget(self.demo_btn)
        button_layout_row_a.addWidget(self.export_btn)
        button_layout_row_b.addWidget(self.export_reset_button)
        button_layout_row_b.addWidget(self.export_exit_button)
        button_layout.addWidget(self.export_button_label)
        button_layout.addLayout(button_layout_row_a)
        button_layout.addLayout(button_layout_row_b)

        export_layout.addStretch(1)
        export_layout.addWidget(self.export_label)
        export_layout.addStretch(1)
        export_layout.addLayout(button_layout)
        export_page.setLayout(export_layout)
    
        return export_page

    def demo_page_generator(self):
        demo_page = QWidget()
        demo_layout = QVBoxLayout()
        button_layout = QHBoxLayout()
        self.vertical_label = QLabel(f"Altura atual: {0}")
        self.exit_button = QPushButton("Sair", clicked=self.close)
        self.demo_reset_button = QPushButton("Novo Pulo", clicked=self.reset_demo_page)
        self.demo_label = QLabel()
        self.demo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        button_layout.addWidget(self.demo_reset_button)
        button_layout.addWidget(self.exit_button)
        button_layout.addWidget(self.vertical_label)
        demo_layout.addWidget(self.demo_label)
        demo_layout.addLayout(button_layout)
        demo_page.setLayout(demo_layout)
        self.demo_timer = QTimer(self)
        self.demo_timer.timeout.connect(self.update_demo_display)
        return demo_page

    '''----- Config Page Helpers ----- '''

    def confirm_config(self):
        valid_set = True
        upload_name = self.upload_line.text()
        jumper_name = self.name_line.text()
        jumper_height = self.height_line.text()
        ref_style = -1 + (1 * self.style_ground.isChecked()) + (2 * self.style_rim.isChecked())
        vid_format = -1 + (1 * self.vid_vert.isChecked()) + (2 * self.vid_landscape.isChecked())
        

        if upload_name == "" or jumper_name == "" or jumper_height=="":
            self.log.info("TEXT FIELDS NOT ENTERED")
            valid_set = False

        if valid_set:
            jumper_height = float(jumper_height)
            self.log.info(f"Upload Path: {upload_name}")
            self.log.info(f"Jumper Name: {jumper_name}")
            self.log.info(f"Jumper Height: {jumper_height}")
            self.log.info(f"Jump Style Index: {ref_style}")
            self.log.info(f"Video Format: {vid_format}")
            
            #----------- Calibration Handler Setup ------------------- IMPORTANT#
            self.ch = CalibrationHandler(source_name=upload_name, jumper_name=jumper_name, jumper_height=jumper_height, jump_style=ref_style, vid_format=vid_format, log=self.log)
            self.ch.generate_video_points()
            self.ch.define_joint_averages()
            self.ch.define_stages()
            self.ch.get_reference_values()
            if ref_style == 0:
                self.ch.estimate_head_height()
            else:
                self.ch.estimate_rim_height()

            self.cal_scale = self.calibration_page_generator(ref_style)
            self.export_p = self.export_page_generator()
            self.demo = self.demo_page_generator()

            self.stackedLayout.addWidget(self.cal_scale)
            self.stackedLayout.addWidget(self.export_p)
            self.stackedLayout.addWidget(self.demo)
            
            self.next_page()

        else:
            self.config_set_msg.setText("Error: Ensure all configuration settings are complete")

    def get_video_file(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', 
            '.\\vid_src',"Video Files (*.mov *.mp4 *.avi)")
        self.upload_line.clear()
        self.upload_line.insert(fname[0])

    '''----- Calibration Page Helpers ----- '''

    def increase_shoulder_offset(self):
        self.shoulder_offset -= 1
        self.update_calibration_img()

    def decrease_shoulder_offset(self):
        self.shoulder_offset += 1
        self.update_calibration_img()

    def increase_rim_offset(self):
        self.rim_offset -= 3
        self.update_calibration_img(ref_style=1)

    def decrease_rim_offset(self):
        self.rim_offset += 3
        self.update_calibration_img(ref_style=1)

    def increase_ground_offset(self):
        self.ground_offset -= 3
        self.update_calibration_img(ref_style=1)

    def decrease_ground_offset(self):
        self.ground_offset += 3
        self.update_calibration_img(ref_style=1)

    def rim_frame_forward(self):
        self.frame_offset = 1
        self.update_calibration_img(ref_style=1)

    def rim_frame_back(self):
        self.frame_offset = -1
        self.update_calibration_img(ref_style=1)


    def confirm_offset(self):
        self.ch.calibrate_measured_height(self.shoulder_offset, self.rim_offset, self.ground_offset)
        self.measured_jump_height = self.ch.calculate_vertical_jump()
        self.export_label.setText(f"Vertical Jump: {self.measured_jump_height*2.5:.2f} cm")
        self.next_page()
    
    def update_calibration_img(self, ref_style=0):
        if ref_style:
            #Get frame of frame offset
            #Draw on that shit
            #Do MATH from there
            if self.frame_offset != 0:
                self.ch.get_incremented_launch_frame(self.frame_offset)
                self.frame_offset = 0
            init_frame = self.ch.get_adjusted_launch_frame(self.ground_offset, self.rim_offset)
            frame_img = Image.fromarray(init_frame)
            self.__calibration_qImg = ImageQt(frame_img)
            self.kin_pixmap = QPixmap.fromImage(self.__calibration_qImg)
            self.calibration_label.setPixmap(self.kin_pixmap)
            self.calibration_label.update()
        else:
            init_frame = self.ch.get_adjusted_head_frame(self.shoulder_offset)
            frame_img = Image.fromarray(init_frame)
            self.__calibration_qImg = ImageQt(frame_img)
            self.kin_pixmap = QPixmap.fromImage(self.__calibration_qImg)
            self.calibration_label.setPixmap(self.kin_pixmap)
            self.calibration_label.update()

    '''----- Demo Page Helpers ----- '''
    
    def setup_demo_page(self):
        self.ch.setup_demo()
        self.demo_timer.start(int(1000/self.frame_rate_demo))

        self.next_page()
    
    def update_demo_display(self):
        vert, frame = np.copy(self.ch.get_demo_frame())
        frame_img = Image.fromarray(frame)
        self.__demo_qImg = ImageQt(frame_img)
        self.kin_pixmap = QPixmap.fromImage(self.__demo_qImg)
        self.demo_label.setPixmap(self.kin_pixmap)
        self.vertical_label.setText(f"Current Height: {vert*2.54}")
        self.demo_label.update()

    def reset_demo_page(self):
        self.demo_timer.stop()
        self.demo_time = None
        self.reset_page()