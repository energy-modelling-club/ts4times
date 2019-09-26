# -*- coding: utf-8 -*-
"""
Created on Tue May 28 13:42:57 2019

@author: Matteo D'Andrea
"""

###################### LYBRARIES AND PACKAGES #################################
import numpy as np
import pandas as pd 
import holidays 

########################## USER INPUTS #######################################
#type the year 
year=2011

################## LOAD & INPUT DATA PREPROCESSING  ##########################
#load the timeseries
#input: matrix N rows and N columns 
InputData=pd.read_csv('inputData.csv')
#load the parameters used to define the Levels (H,M,L)
#the # of columns must be greater by 1 than the inputData
Param=pd.read_csv('levelParam.csv')

#set the time period interested 
startDate='01-01-'+ str(year)
endDate='01-01-'+ str(year+1)

#date_range keys: 
#freq: Hourly frequency
#closed: upper bound not included (i.e 01-01-2012 00:00)
Date=pd.DataFrame(pd.date_range(start=startDate, end=endDate,\
                                 freq='H', closed='left'))

#The input is stored in a matrix with the date as first column
InputData=pd.concat([Date,InputData],axis=1)
InputData.rename(columns={0:'Date'},inplace=True)

###################### BUSINESS DAY AND SEASONS ##############################
#this package containes the holidays of each state
#Denmark is selected and the year previously defined 
DK_holidays = holidays.Denmark(years = year) 

#Legend: 
#seasons
    #R: spring
    #S: summer 
    #F: fall
    #W: winter 
#business day
    #WD: weekday
    #NW: non weekday
    
#assign a letter given the corresponding season
season=pd.cut(InputData.Date.dt.month, bins=[0, 2, 5, 8, 11,12],\
              labels=['W1', 'R', 'S','F','W2'])
season=season.replace(['W1','W2'], ['W','W'])
#assign a code for working/non-working day 
bday=pd.Series(np.where(InputData.Date.dt.date.isin(DK_holidays),'NW' , \
              pd.cut(InputData.Date.dt.dayofweek+1, bins=[1, 5, 7],\
              include_lowest=True,labels=['WD', 'NW'])))

######################## LEVEL CHECK ########################################
#calculate the mean over the columns 
avg=np.mean(InputData.iloc[:,1:],axis=0)

#a vector of zeros is initialized 
levelMatrix=np.zeros((InputData.shape[0],1))

#Level legend:
# High=   3
# Medium= 2
# Low=    1

#the process is repeated for every column 
for j in range(0,InputData.shape[1]-1):
    #two vectors are initiliazed for the concatenation process
    levelArray=np.zeros((InputData.shape[0],1))
    levelMatrixBool=np.zeros((InputData.shape[0],1),dtype=int)
    for i in season.unique():
        cond1=Param.Season==i
        cond2=Param.Level==2
        cond3=Param.Level==1
        #the vector with the levels is generated 
        level=np.where(InputData.iloc[:,j+1]>avg[j]*\
                   Param.loc[cond1 & cond2].iloc[0,j+2],'3' ,\
                         np.where(InputData.iloc[:,j+1] > avg[j]*\
                                  Param.loc[cond1 & cond3].iloc[0,j+2],'2' ,'1'))
        #a matrix is generated with the results
        levelArray=np.append(levelArray,level.reshape(InputData.shape[0],1),axis=1)
        #a matrix of boolean numbers is obtained to filter the desidered values
        vec=season==i
        levelMatrixBool=np.hstack((levelMatrixBool,vec.values.reshape(InputData.shape[0],1)))
    #a boolean mask is created and summed over the rows to obtain a vector
    boolMask=pd.DataFrame(levelArray[levelMatrixBool ==1])
    levelVector=np.nansum(boolMask,dtype=int, axis=1)    
    #a level vector for each inputData column is obtain and stored in a matrix
    levelMatrix=np.append(levelMatrix,levelVector.reshape(InputData.shape[0],1),axis=1)
    
levelMatrix=pd.DataFrame(levelMatrix[:,1:])

#%%             
####################### ABCD Cases ##########################################
# given the input data the respective case is found. 
#A = P:L, PV:All, W:H
#B = P:H, PV:All, W:L
#C = P:All, PV:L, W:All
#D = Rest
            
Timeslice=[]
for i in range(InputData.shape[0]):  
    if levelMatrix.iloc[i,0]==1 and  levelMatrix.iloc[i,3]==3:
        Timeslice.append(season[i]+bday[i]+'A')
    elif levelMatrix.iloc[i,0]==3 and  levelMatrix.iloc[i,3]==1:
        Timeslice.append(season[i]+ bday[i]+'B')
    elif   levelMatrix.iloc[i,2]==1 :
        Timeslice.append(season[i]+bday[i]+'C')
    else:
         Timeslice.append(season[i]+bday[i]+'D')
         
Timeslice=pd.DataFrame(Timeslice)
#add the timeslice to the input data as the second column 
InputData=pd.concat([InputData.Date,Timeslice,InputData.iloc[:,1:]],axis=1)
InputData.rename(columns={0:'Timeslice'},inplace=True)
#%%
###################### OUTPUT ################################################

#export the input data and the timeslice to excel 
InputData.to_excel (r'output.xlsx', index = None, header=True)

#export Timeslice to csv 
Timeslice.to_csv('Timeslices.csv',index=False)
#%%
################### results analysis ##########################################
#analysis on the aggregated power and time of each unique time slice

#the total power is calculated for each input column 
maximumPower=np.sum(InputData.iloc[:,2:],axis=0)
#a row fo zeros must be initiliazed to use np.append at first iteration
AveragePower=np.zeros((1,InputData.shape[1]-2))

#an empty list is inizialiated to contain the tot. number of hours per timeslice
hours=[]
for i in InputData.Timeslice.unique():
        #obtain the average power given the unique timeslice
        vec=(np.sum(InputData.loc[InputData.Timeslice==i].iloc[:,2:],axis=0)/maximumPower)
        #count the hours for each unique timeslice
        hours.append(InputData.loc[InputData.Timeslice==i].iloc[:,2:].shape[0])
        #append  vertically the averages found to form a matrix 
        AveragePower=np.append(AveragePower,vec.values.reshape(1,InputData.shape[1]-2),axis=0)
        
#subtract the first row of zeros and convert to dataframe
AveragePower=pd.DataFrame(AveragePower[1:,:])
AveragePower.rename(columns={0:'PowerDemand',1:'Heat Demand',2:'PV',3:'WInd'},\
                    inplace=True)

#create a dataframe with the unique Timeslices
UniqueTimeslice=pd.DataFrame(InputData.Timeslice.unique())
UniqueTimeslice.rename(columns={0:'Timeslice'},inplace=True)

#create a df to store the results
#columns: unique timeslice, # of hours, % of total time, average powers

TimesliceAggregation=pd.concat([UniqueTimeslice,pd.Series(hours),\
                           pd.Series(hours)/InputData.shape[0],AveragePower],axis=1)
    
TimesliceAggregation.rename(columns={0:'# hours',1:'% hours'},inplace=True)

#export to excel the results 
TimesliceAggregation.to_excel (r'TimesliceAggregation.xlsx', index = None, header=True)
#export to csv the results 
TimesliceAggregation.to_csv('TimesliceAggregation.csv',index=False)