#include <stdint.h>

static inline float clamp255(float value)
{
	if (value < 0.0f)
	return 0.0f;
	
	if (value > 255.0f)
	return 255.0f;
	
	return value;
}

void atkinson_dither(
					 float *source,
					 uint8_t *output,
					 int width,
					 int height
					 ) {
	for (int y = 0; y < height; y++) {
		for (int x = 0; x < width; x++) {
			int i = y * width + x;
			
			float old_value = source[i];
			float new_value =
					(old_value >= 128.0f) ? 255.0f : 0.0f;
			
			output[i] = (uint8_t)new_value;
			
			float error =
					(old_value - new_value) / 8.0f;
			
			if (x + 1 < width) {
				source[i + 1] =
						clamp255(source[i + 1] + error);
			}
			
			if (x + 2 < width) {
				source[i + 2] =
						clamp255(source[i + 2] + error);
			}
			
			if (y + 1 < height) {
				int next = i + width;
				
				if (x > 0) {
					source[next - 1] =
							clamp255(source[next - 1] + error);
				}
				
				source[next] =
						clamp255(source[next] + error);
				
				if (x + 1 < width) {
					source[next + 1] =
							clamp255(source[next + 1] + error);
				}
			}
			
			if (y + 2 < height) {
				source[i + 2 * width] =
						clamp255(source[i + 2 * width] + error);
			}
		}
	}
}