################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (14.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../STM_SHELL/Src/shell.c \
../STM_SHELL/Src/shell_commands.c 

OBJS += \
./STM_Shell/Src/shell.o \
./STM_Shell/Src/shell_commands.o 

C_DEPS += \
./STM_Shell/Src/shell.d \
./STM_Shell/Src/shell_commands.d 


# Each subdirectory must supply rules for building sources it contributes
STM_Shell/Src/shell.o: C:/tools/OneDrive\ -\ Höhere\ technische\ Bundeslehranstalt\ Graz-Gösting/hw/g4/DC-Motor-Board/fw/pcb/STM_SHELL/Src/shell.c STM_Shell/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DSHELL_ROOT_BLOCK -DSHELL_NO_LED -DUSE_FULL_LL_DRIVER -DUSE_HAL_DRIVER -DSTM32G431xx -c -I../Core/Inc -I../Drivers/STM32G4xx_HAL_Driver/Inc -I../Drivers/STM32G4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32G4xx/Include -I../Drivers/CMSIS/Include -I"C:/tools/OneDrive - Höhere technische Bundeslehranstalt Graz-Gösting/hw/g4/DC-Motor-Board/fw/pcb/STM_SHELL/Inc" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"
STM_Shell/Src/shell_commands.o: C:/tools/OneDrive\ -\ Höhere\ technische\ Bundeslehranstalt\ Graz-Gösting/hw/g4/DC-Motor-Board/fw/pcb/STM_SHELL/Src/shell_commands.c STM_Shell/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DSHELL_ROOT_BLOCK -DSHELL_NO_LED -DUSE_FULL_LL_DRIVER -DUSE_HAL_DRIVER -DSTM32G431xx -c -I../Core/Inc -I../Drivers/STM32G4xx_HAL_Driver/Inc -I../Drivers/STM32G4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32G4xx/Include -I../Drivers/CMSIS/Include -I"C:/tools/OneDrive - Höhere technische Bundeslehranstalt Graz-Gösting/hw/g4/DC-Motor-Board/fw/pcb/STM_SHELL/Inc" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-STM_Shell-2f-Src

clean-STM_Shell-2f-Src:
	-$(RM) ./STM_Shell/Src/shell.cyclo ./STM_Shell/Src/shell.d ./STM_Shell/Src/shell.o ./STM_Shell/Src/shell.su ./STM_Shell/Src/shell_commands.cyclo ./STM_Shell/Src/shell_commands.d ./STM_Shell/Src/shell_commands.o ./STM_Shell/Src/shell_commands.su

.PHONY: clean-STM_Shell-2f-Src

