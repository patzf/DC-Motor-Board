/*
 * shell_pfs.c
 *
 * Application-specific PFS (Pseudo File System) defining the commands the user can execute through the shell.
 *
 * This is a TEMPLATE with a few EXAMPLE commands you may delete.
 * Hardware-specific LED macro requires a GPIO (output) pin labelled "LED".
 *
 * This file contains :
 *
 * - Command functions (the implementation of shell commands)
 * - Command blocks (linked-list forming a hierarchical tree of commands)
 *
 *  Created on: May 13, 2022
 *  Author: Jean Roch - Nefastor.com
 *
 *  Copyright 2022 Jean Roch
 *
 *  This file is part of STM Shell.
 *
 *  STM Shell is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
 *  as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
 *
 *  STM Shell is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
 *  of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License along with STM Shell.
 *  If not, see <https://www.gnu.org/licenses/>.
 */

#include "shell.h"

#include "main.h"	   // For the HAL
#include "gitcommit.h" //to get version string of last commit
#include "motor_control.h"

#include <stdio.h>
#include <string.h>	// For strlen



// Macros for programming command functions more easily :
// Start a state machine:
#define STATE_MACHINE static int state = 0; switch (state) {
// Start a state machine state:
#define STATE break; case
// End a state machine:
#define STATE_MACHINE_END }
// Return from state machine (can be used in any state) :
#define RETURN state = 0; shell_fp = shell_state_output; shell_state.command_fp = 0;
// End a command function:
#define DONE shell_fp = shell_state_output; shell_state.command_fp = 0;

// LED control macro. This is hardware specific, make sure "LED" refers to the correct pin on your target.
// If your board doesn't have an LED, define SHELL_NO_LED to replace with a dummy macro
#ifndef SHELL_NO_LED
#define LED(a) HAL_GPIO_WritePin(LED_GPIO_Port, LED_Pin, ((a) == 1) ? GPIO_PIN_SET : GPIO_PIN_RESET)
#else
#define LED(a)
#endif

/////////////////////////////////////////////////////////////////////////////////////
// Command functions : your application-specific commands are implemented here
// Naming convention : command function names should start with "command_"
// (Documentation on nefastor.com)
/////////////////////////////////////////////////////////////////////////////////////

#define USING_STATE_MACHINE_MACROS

// Command that returns the number of times it's been called :
// This illustrates the use of static variables to store data between calls to the same command,
// in the absence of an actual filesystem.
#ifndef USING_STATE_MACHINE_MACROS
void command_cnt ()
{
	static int cnt = 0;		// counter
	static int state = 0;	// the command's own state machine's current state

	switch (state)
	{
		case 0:
			sprintf (shell_state.output, "\r\nCalled %i times", cnt);
			shell_fp = shell_state_output;		// Use the shell's own output function
			state = 1;							// Transition to next state
			break;								// Yield the CPU back to the application
		case 1:
			cnt++;
			state = 0;
			shell_state.command_fp = 0;			// Ends this command's execution
			shell_fp = shell_state_output;		// This time, it'll return to the prompt
			break;
	}
}
#else
// Same function but using the helper macros
void command_cnt ()
{
	static int cnt = 0;		// counter

	STATE_MACHINE
	STATE 0:
		sprintf (shell_state.output, "\r\nCalled %i times", cnt);
		shell_fp = shell_state_output;		// Use the shell's own output function
		state = 1;							// Transition to next state
	STATE 1:
		cnt++;
		RETURN
	STATE_MACHINE_END
}

#endif

#ifndef SHELL_NO_LED
// LED toggle :
// This is an example of a command so simple it executes in one call and doesn't require a state machine
void command_led_toggle ()
{
	HAL_GPIO_TogglePin(LED_GPIO_Port, LED_Pin);

	// Transition back to the prompt
	shell_fp = shell_state_output;	// transition to output state...
	shell_state.command_fp = 0;		// ... but this command ends, so we'll be returning to the prompt

	// DONE
}
#endif

// Demo function : designed to waste some time, display some stuff. Used for debugging the shell itself.
void command_load ()
{
	static int cnt = 0;
	static int state = 0;
	static volatile long long accu = 0;
	int k;

	switch (state)
	{
		case 0:		// wait for previous DMA transfer to complete, and then transition
			if (shell_state.busy == 0)
				state = 1;
			break;
		case 1:		// send out the counter's value as a string and increment
			// Print straight to the output buffer
			sprintf (shell_state.output, "\r\nValues : %i %li", cnt++, (long) (accu / 10000));
			shell_fp = shell_state_output;	// transition to output state
			state = 2;	// transition to local state 2.
			break;
		case 2:		// end test
			state = 0;		// loop back to keep counting or reset the state machine
			if (cnt == 500)
			{
				cnt = 0;							// clear the counter
				shell_fp = shell_state_output;	// transition to output state...
				shell_state.command_fp = 0;		// ... but this command ends, so we'll be returning to the prompt
			}
			else
			{
				// Do some time-wasting processing (load check)
				for (k = 0; k < 10000; k++)
					accu += k * cnt;
			}
			break;
	}

}




void command_set_motor_rpm ()
{
	setMotorRPM(5000);
	shell_state.command_fp = 0;			// Ends this command's execution
	shell_fp = shell_state_output;		// This time, it'll return to the prompt
}

//void command_pwm_start ()
//{
//	Start_PWM();
//	shell_state.command_fp = 0;			// Ends this command's execution
//	shell_fp = shell_state_output;		// This time, it'll return to the prompt
//}
//
//void command_pwm_stop ()
//{
//	Stop_PWM();
//	shell_state.command_fp = 0;			// Ends this command's execution
//	shell_fp = shell_state_output;
//}


// Demo function : flash LED "LD3" a number of times, with the number passed as command line argument
// This demonstrates how to parse command line arguments

#ifndef USING_STATE_MACHINE_MACROS
void command_flash ()
{
	static int state = 0;
	static int arg = 0;
	static int delay;		// Controls flashing speed of the LED
	const int max_delay = 100000;
	int rv = 0;

	switch (state)
	{
		case 0:		// parse the command line
			rv = sscanf (shell_state.input, "flash %i", &arg);
			if ((rv == 1) && (arg > 0))		// argument successfully decoded and non-zero ?
				state++;	// Move on to next state
			else
				state = 6;	// Move on to final state (exits the command)
			break;
		case 1:		// turn on the LED
			HAL_GPIO_WritePin(GPIOB, UCPD_DBn_Pin|LED_BLUE_Pin, GPIO_PIN_SET);
			delay = max_delay;
			state++;		// Move on to next state : delay loop
			break;
		case 2:		// delay loop
			if (delay > 0)
				delay--;	// decrement the delay
			else
				state++;	// delay elapsed : go to next state
			break;
		case 3:		// turn off the LED
			HAL_GPIO_WritePin(GPIOB, UCPD_DBn_Pin|LED_BLUE_Pin, GPIO_PIN_RESET);
			delay = max_delay;
			state++;		// Move on to next state : delay loop
			break;
		case 4:		// delay loop
			if (delay > 0)
				delay--;	// decrement the delay
			else
				state++;	// delay elapsed : go to next state
			break;
		case 5:		// decrement arg and test for command completion
			arg--;
			if (arg == 0)
				state++;	// exit
			else
				state = 1;	// loop back
			break;
		case 6:		// command complete, return to prompt
			state = 0;		// reset for next time
			shell_fp = shell_state_output;
			shell_state.command_fp = 0;	// this command has ended
			break;
	}
}
#else
// Same function but this time using macros
void command_flash ()
{
	static int arg = 0;
	static int delay;		// Controls flashing speed of the LED
	const int max_delay = 1000000;	// 100000; way too short if running the H7 at 480 MHz with ICACHE and DCACHE !
	int rv = 0;

	STATE_MACHINE
	STATE 0:		// parse the command line
		rv = sscanf (shell_state.input, "flash %i", &arg);
		state = ((rv == 1) && (arg > 0)) ? 1 : 6;		// argument successfully decoded and non-zero ?
	STATE 1:		// turn on the LED
		LED(1);
		delay = max_delay;
		state++;		// Move on to next state : delay loop
	STATE 2:		// delay loop
		delay--;
		state = (delay > 0) ? 2 : 3;
	STATE 3:		// turn off the LED
		LED(0);
		delay = max_delay;
		state++;		// Move on to next state : delay loop
	STATE 4:		// delay loop
		delay--;
		state = (delay > 0) ? 4 : 5;
	STATE 5:		// decrement arg and test for command completion
		arg--;
		state = (arg == 0) ? 6 : 1;
	STATE 6:		// command complete, return to prompt
		RETURN
	STATE_MACHINE_END
}
#endif


/////////////// DEMONSTATION PFS - REMOVE FROM FINAL PRODUCT //////////////////////////////////////////////////

// Demo root command block, should be declared by the application.
// I need to come up with an initialization mechanism to get the pointer to the shell_state structure.
// TEST ONLY : sub-blocks for navigation testing
t_shell_block_entry level_2_block[] =
{
		{"Submenu 2", BLOCK_LEN 2, 0},	// Title block. Parent block is level 1 block
		{"load - performance test", command_load, 0},		// Demo function
		{"load - performance test", command_load, 0}		// Demo function
};

t_shell_block_entry level_1_block[] =
{
		{"Submenu 1", BLOCK_LEN 3, 0},	// Title block. Parent block is root.
		{"load - performance test", command_load, 0},		// Demo function
		{"load - performance test", command_load, 0},		// Demo function
		{"sm2 - nested submenu example", 0, CMD_BLOCK level_2_block}
};

// The application MUST declare root_block.
// Its first entry's label will always appear at the start of the prompt and should be the device's name
t_shell_block_entry root_block[] =
{
		{GIT_INFO_PRESENT, BLOCK_LEN 5, 0},	// Title block. Root, so no parent block. No function. Function pointer replaced by command count in the block
		//{"sm1 - submenu example", 0, CMD_BLOCK level_1_block},	// Example of submenu declaration
		//{"led - toggles the blue LED", command_led_toggle, 0},
		//{"flash N - flash the LED 'N' times", command_flash, 0},
		//{"cnt - displays its own call count", command_cnt, 0},
		//{"load - performance test", command_load, 0}
		{"setMotorRPM", command_set_motor_rpm, 0}
		//{"startPWM", command_pwm_start, 0},
		//{"stopPWM", command_pwm_stop, 0}
};


