#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <irq.h>
#include <uart.h>
#include <generated/csr.h>
#include <i2c.h>
#include "i2c_spi.h"



enum {
    PIN_SPI_SS = 0,
    PIN_PROG_EN,
    PIN_PROGRAMN,
    PIN_DONE
};

#define SPI_CMD_READ_ID 0x9f


int main(void)
{
#ifdef CONFIG_CPU_HAS_INTERRUPT
    irq_setmask(0);
    irq_setie(1);
#endif
    uart_init();

    uint8_t buf[4] = {0};

    // configure 'programming enable' pin of io expander as gpio output
    buf[0] = 1 << PIN_PROG_EN;
    assert(i2c_write(I2C_ADDR, GPIO_ENABLE, buf, 1));

    // set the pin as push-pull output
    buf[0] = GPIO_MODE_PP << (PIN_PROG_EN * 2);
    assert(i2c_write(I2C_ADDR, GPIO_CONFIG, buf, 1));

    // TODO: it's better to halt ECP5 here using PIN_PROGRAMN

    // enable programming
    // connects SPI lines of the bridge to the flash memory
    // (see schematics)
    buf[0] = 1 << PIN_PROG_EN;
    assert(i2c_write(I2C_ADDR, GPIO_WRITE, buf, 1));

    buf[0] = 0; // SPI mode: max clock rate, CPOL = 0, CPHA = 0, MSB first
    assert(i2c_write(I2C_ADDR, CONFIG_SPI, buf, 1));

    buf[0] = SPI_CMD_READ_ID;
    assert(i2c_spi_write((1 << PIN_SPI_SS), buf, 4));
    assert(i2c_spi_read((1 << PIN_SPI_SS), buf, 4));
    printf("SPI flash ID: %d %d %d %d\n", buf[0], buf[1], buf[2], buf[3]);

    // disable programming
    buf[0] = 0;
    assert(i2c_write(I2C_ADDR, GPIO_WRITE, buf, 1));

    // TODO: check PIN_DONE

    while(1) {}

    return 0;
}
