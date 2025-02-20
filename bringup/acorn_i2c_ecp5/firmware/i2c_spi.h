#include <stdbool.h>
#include <stdint.h>

// see SC18IS602B I2C-SPI bridge datasheet

#define I2C_ADDR 0x28

#define GPIO_WRITE 0xf4
#define GPIO_READ 0xf5
#define GPIO_ENABLE 0xf6
#define GPIO_CONFIG 0xf7
#define CONFIG_SPI 0xf0

#define GPIO_MODE_PP 0b01

bool i2c_spi_write(uint8_t ss, uint8_t *data, unsigned len);
bool i2c_spi_read(uint8_t ss, uint8_t *data, unsigned len);
