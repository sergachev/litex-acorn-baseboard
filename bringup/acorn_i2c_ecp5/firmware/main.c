#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <irq.h>
#include <uart.h>
#include <generated/csr.h>
#include <i2c.h>
#include "i2c_spi.h"


int main(void)
{
#ifdef CONFIG_CPU_HAS_INTERRUPT
    irq_setmask(0);
    irq_setie(1);
#endif
    uart_init();

    while(1) {}

    return 0;
}
