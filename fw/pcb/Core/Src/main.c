/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "adc.h"
#include "dma.h"
#include "i2c.h"
#include "usart.h"
#include "tim.h"
#include "ucpd.h"
#include "usb.h"
#include "gpio.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "shell.h"

//TODO FIXME
HAL_StatusTypeDef DMA_status;
volatile uint16_t err = 0;
volatile uint8_t dfu_jump_requested;

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */



/* STM Shell related */

void shell_out (char *buff, int length)
{
  HAL_UART_Transmit_DMA(&hlpuart1, (uint8_t *) buff, length);
  shell_state.busy = 1;  // DMA transfer in progress.
}

void shell_get_byte (char *c)
{
  HAL_UART_Receive_IT(&hlpuart1, (uint8_t *) c, 1);
}

/*
void HAL_UART_TxCpltCallback (UART_HandleTypeDef *huart)
{
  // Verify which USART we're dealing with:
  if (huart->Instance == LPUART1)  // UART used by the shell
    shell_state.busy = 0;  // Transfer complete : clear the flag
}
*/

void HAL_UART_RxCpltCallback (UART_HandleTypeDef *huart)
{
  // Verify which USART we're dealing with :
  if (huart->Instance == LPUART1)  // UART used by the shell
    shell_in (shell_state.c);  // Feed the byte to the shell
}





// Taken from https://community.st.com/stm32-mcus-60/how-to-jump-to-system-bootloader-from-application-code-on-stm32-microcontrollers-71
#include "stm32g4xx_hal.h"
#include "core_cm4.h"

#define SYSTEM_MEMORY_BASE 0x1FFF0000UL
typedef void (*pFunction)(void);

void JumpToSystemBootloader(void)
{
    uint32_t sp = *(volatile uint32_t *)(SYSTEM_MEMORY_BASE + 0);
    uint32_t pc = *(volatile uint32_t *)(SYSTEM_MEMORY_BASE + 4);
    pFunction bootloader = (pFunction)pc;

    __disable_irq();
    SysTick->CTRL = 0;
    SysTick->LOAD = 0;
    SysTick->VAL = 0;

    for (uint32_t i = 0; i < sizeof(NVIC->ICER) / sizeof(NVIC->ICER[0]); i++)
    {
        NVIC->ICER[i] = 0xFFFFFFFFUL;
        NVIC->ICPR[i] = 0xFFFFFFFFUL;
    }

    HAL_RCC_DeInit();

    __set_MSP(sp);
    __enable_irq();
    bootloader();

    while (1) {}
}











void cycleThrough(void)
{
	// Spin through duty cycles 90%, 80%, .... 10%
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


// Just spin the motor in forward direction with 100% duty cycle
void quickCheck(void)
{
	__HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, 6800); // always high for 100% duty cycle
	__HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_2, 0); // keeping that zero uses coast mode

	HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_2);
	HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
}


// Prepare TIM2 for counting pulses.
// We count the number of pulses inside a fixed time window of 1ms
// at no load : HALL Sensor delivers pulses with 2.8kHz -> 2.8kHz/16 = 175 RPS = 175*60 = 10500 RPM
// in 1ms, we would count 2.8 pulses
// we need to count at least 2 pulses to estimate frequency.
// With 16 RPC
// -> if we want to measure down to 1 RPS we need to wait for at least 2*1/*16 = 125ms
// -> for measuring 10RPS, we need to measure for 12,5ms
// if we wait for 10ms, we can measure down to ~ 2/16 turns/10ms = 1/8*100 = 12.5 RPS
//TODO: currently we do not make use of the parameter rpm
void measStepRsp(uint16_t rpm)
{
	HAL_TIM_Base_Start_IT(&htim3); // this will fire period elapsed callback on TIM3 overrun
	HAL_TIM_IC_Start_IT(&htim2, TIM_CHANNEL_1); // this will enable TIM2 that is counting pulses with input capture

	__HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, 6800); // always high for 100% duty cycle
	__HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_2, 0); // keeping that zero uses coast mode during off time of PWM

	HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_2);
	HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
}

void startAdcSampling(void)
{
	HAL_ADCEx_Calibration_Start(&hadc2, ADC_SINGLE_ENDED);
	HAL_ADC_Start_DMA(&hadc2, (uint32_t *)adc_buffer, ADC_BUFFER_SIZE);
	HAL_TIM_Base_Start(&htim4); // TIM4 Update event triggers ADC
}



/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_DMA_Init();
  MX_ADC1_Init();
  MX_ADC2_Init();
  MX_LPUART1_UART_Init();
  MX_UCPD1_Init();
  MX_TIM2_Init();
  MX_TIM1_Init();
  MX_I2C1_Init();
  MX_TIM3_Init();
  MX_TIM4_Init();
  MX_USB_PCD_Init();
  /* USER CODE BEGIN 2 */

  __HAL_DBGMCU_FREEZE_TIM4();

  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */

/*  while (!USB_DeviceIsConfigured())
  {
      // USB enumeration is still in progress
  }*/

  //setMotorRPM(0);
 // HAL_Delay(2000); //just to spin up
 // setMotorRPM(3000);

  //startAdcSampling();

  //quickCheck();
  //cycleThrough();
  //HAL_Delay(3000);

  HAL_Delay(5000);
  measStepRsp(6800);

  while (1)
  {
	  /* !! DO NOT MODIFY THIS !! */
	  if(dfu_jump_requested)
	  {
		  JumpToSystemBootloader();
	  }

	  // Keep shell interaction going
	  shell_fp();

	  //stop measurement and send data to PC when step response has finished
	  if(f_measurement_finished)
	  {
		HAL_TIM_Base_Stop_IT(&htim3);
		HAL_TIM_IC_Stop(&htim2, TIM_CHANNEL_1);

		HAL_TIM_PWM_Stop(&htim1, TIM_CHANNEL_1);
		HAL_TIM_PWM_Stop(&htim1, TIM_CHANNEL_2);

		//send values to PC
		HAL_UART_Transmit(&hlpuart1, (uint8_t*)motor_rpm, sizeof(motor_rpm), HAL_MAX_DELAY);
		f_measurement_finished = 0;
		//memset(motor_rpm, 0, sizeof(motor_rpm));
	  }


	  /*
	  if(convHalfComplete)
	  {
		// ADC has finished writing Part A of buffer
		// Since uart is configured for 8 bit/ no party, the size parameter is also interpreted in bytes
		DMA_status = HAL_UART_Transmit_DMA(&hlpuart1, (uint8_t *) &adc_buffer[0], ADC_BUFFER_SIZE/2*sizeof(uint16_t));
		//status = CDC_Transmit_FS( (uint8_t *)&adc_buffer[0], ADC_BUFFER_SIZE / 2 * sizeof(uint16_t) );
//		if (status != USBD_OK)
//		{
//			err=2;
//		}
		convHalfComplete = 0;
	  }

	  if(convComplete)
	  {

		//status = CDC_Transmit_FS( (uint8_t *)&adc_buffer[ADC_BUFFER_SIZE / 2], ADC_BUFFER_SIZE / 2 * sizeof(uint16_t) );
		DMA_status = HAL_UART_Transmit_DMA(&hlpuart1, (uint8_t *) &adc_buffer[ADC_BUFFER_SIZE/2], ADC_BUFFER_SIZE/2*sizeof(uint16_t));
//		if (status != USBD_OK)
//		{
//			err=2;
//		}
		convComplete = 0;
	  }
	  */


    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE1_BOOST);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI|RCC_OSCILLATORTYPE_HSI48;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.HSI48State = RCC_HSI48_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLM = RCC_PLLM_DIV4;
  RCC_OscInitStruct.PLL.PLLN = 85;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
  RCC_OscInitStruct.PLL.PLLQ = RCC_PLLQ_DIV4;
  RCC_OscInitStruct.PLL.PLLR = RCC_PLLR_DIV2;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_4) != HAL_OK)
  {
    Error_Handler();
  }
}

/* USER CODE BEGIN 4 */




/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
