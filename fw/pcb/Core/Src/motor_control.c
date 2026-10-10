/*
 * motor_control.c
 *
 *  Created on: 10 Oct 2026
 *      Author: franz
 */

#include "motor_control.h"

void setMotorRPM(uint32_t rpm)
{
	// TODO: remove the hardcoded 6800 form TIM1

	// calc duty cycle needed for given RPM

	// Annahme: linearer Zusammenhang zwischen RPM und UMOTOR
	// UMotor = rpm/10000.0f*12;

	// Annahme: linearer Zusammenhang zwischen UMOTOR und PWM duty cycle
	// duty in prozent = UMotor/12.0f*100
	// 100% duty heißt: TIMER capture compare = Timer overflow (Period)
	// Timer CCR = UMotor/12.0f*6800

	uint32_t duty = rpm*68/100.0f;

	__HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_2, 0);
	__HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, duty);
	HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
	HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_2);

}

void setMotorDuty(void)
{
	__HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, 0);
	__HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_2, 0);
	HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
	HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_2);
	for(int i = 10; i >= 1; i--)
	{
		int duty = i*680;
		__HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, duty);
		HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
		HAL_Delay(5000);
		HAL_TIM_PWM_Stop(&htim1, TIM_CHANNEL_1);
		HAL_Delay(3000);
	}
}


