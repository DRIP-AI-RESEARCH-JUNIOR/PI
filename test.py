import cv2
import json
import torch
import Assistant
import numpy as np
from copy import deepcopy
from data_loader import Generator
import time
from parameters import Parameters
import util
from tqdm import tqdm
import csaps

p = Parameters()




def Testing():
    print('Testing')
    
    #########################################################################
    ## Get dataset
    #########################################################################
    print("Get dataset")
    loader = Generator()

    ##############################
    ## Get agent and model
    ##############################
    print('Get agent')
    if p.model_path == "":
        lane_assistant = Assistant.Assistant()
    else:
        lane_assistant = Assistant.Assistant()
        lane_assistant.load_weights(804, "tensor(0.5786)")
	
    ##############################
    ## Check GPU
    ##############################
    print('Setup GPU mode')
    if torch.cuda.is_available():
        lane_assistant.cuda()

    ##############################
    ## testing
    ##############################
    print('Testing loop')
    lane_assistant.evaluate_mode()

    if p.mode == 0 : # check model with test data 
        for _, _, _, test_image in loader.Generate():
            _, _, ti = test(lane_assistant, np.array([test_image]))
            cv2.imshow("test", ti[0])
            cv2.waitKey(0)
	
    elif p.mode == 1: # check model with video
        cap = cv2.VideoCapture("abc.mp4")
        while(cap.isOpened()):
            ret, frame = cap.read()
            torch.cuda.synchronize()
            prevTime = time.time()
            frame = cv2.resize(frame, (512,256))/255.0
            frame = np.rollaxis(frame, axis=2, start=0)
            _, _, ti = test(lane_agent, np.array([frame])) 
            curTime = time.time()
            sec = curTime - prevTime
            fps = 1/(sec)
            s = "FPS : "+ str(fps)
            ti[0] = cv2.resize(ti[0], (1280,800))
            cv2.putText(ti[0], s, (0, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0))
            cv2.imshow('frame',ti[0])
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()
	
    elif p.mode == 2: # check model with a picture
        test_image = cv2.imread(p.test_root_url+"clips/0530/1492720840345996040_0/20.jpg")
        test_image = cv2.resize(test_image, (512,256))/255.0
        test_image = np.rollaxis(test_image, axis=2, start=0)
        _, _, ti = test(lane_agent, np.array([test_image]))
        cv2.imshow("test", ti[0])
        cv2.waitKey(0)
	
	
############################################################################
## test on the input test image
############################################################################
def test(lane_agent, test_images, thresh = p.threshold_point, index= -1):

    result = lane_agent.predict_lanes_test(test_images)
    torch.cuda.synchronize()
    confidences, offsets, instances = result[index]
    
    num_batch = len(test_images)

    out_x = []
    out_y = []
    out_images = []
    
    for i in range(num_batch):
        # test on test data set
        image = deepcopy(test_images[i])
        image = np.rollaxis(image, axis=2, start=0)
        image = np.rollaxis(image, axis=2, start=0)*255.0
        image = image.astype(np.uint8).copy()

        confidence = confidences[i].view(p.grid_y, p.grid_x).cpu().data.numpy()

        offset = offsets[i].cpu().data.numpy()
        offset = np.rollaxis(offset, axis=2, start=0)
        offset = np.rollaxis(offset, axis=2, start=0)
        
        instance = instances[i].cpu().data.numpy()
        instance = np.rollaxis(instance, axis=2, start=0)
        instance = np.rollaxis(instance, axis=2, start=0)

        # generate point and cluster
        raw_x, raw_y = generate_result(confidence, offset, instance, thresh)

        # eliminate fewer points
        in_x, in_y = eliminate_fewer_points(raw_x, raw_y)
                
        # sort points along y 
        in_x, in_y = util.sort_along_y(in_x, in_y)  

        result_image = util.draw_points(in_x, in_y, deepcopy(image))

        out_x.append(in_x)
        out_y.append(in_y)
        out_images.append(result_image)
        
    return out_x, out_y,  out_images
