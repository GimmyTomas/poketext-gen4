//
//  main.cpp
//  poketext-gen4
//
//  Created by Giovanni Maria Tomaselli on 19/01/24.
//

/*
 Compile on Xcode (Apple Silicon):
 
 Other linker flags: -I/opt/homebrew/include/ -L/opt/homebrew/lib/ -lleptonica -ltesseract -lavcodec -lavformat -lswscale
  
 Header search paths: /opt/homebrew/include
 */

#include <iostream>
#include <string.h>
#include <fstream>
#include <tesseract/baseapi.h>
#include <leptonica/allheaders.h>

extern "C"
{
    #include <libavcodec/avcodec.h>
    #include <libavformat/avformat.h>
    #include <libavfilter/buffersink.h>
    #include <libavfilter/buffersrc.h>
    #include <libavutil/opt.h>
    #include <libswscale/swscale.h>
}

AVFormatContext *fmt_ctx;
AVCodecContext *dec_ctx;
int video_stream_index = -1;

struct coords {
    int x;
    int y;
};

struct rectangle_coords {
    coords top_left;
    int x_size;
    int y_size;
    double magnification = 0;
};

void top_screen_coords(rectangle_coords & result)
{
    result.top_left.x = dec_ctx->width/4;
    result.top_left.y = 0;
    result.x_size = dec_ctx->width - result.top_left.x;
    result.y_size = dec_ctx->height;
    result.magnification = (double) (dec_ctx->width - result.top_left.x) / 256;
}

// check if a given rectangle in the image is white (all three colors above color_intensity), with some specified tolerance (non_white_strictness)
bool white_rectangle(unsigned char *data, int wrap, rectangle_coords & rectangle, double non_white_strictness, int color_intensity)
{
    unsigned char *pixel;
    
    int white = 0;
    int not_white = 0;
    for (int i = rectangle.top_left.y; i < rectangle.top_left.y + rectangle.y_size; i++)
    {
        pixel = data + i * wrap + 3 * rectangle.top_left.x;
        for (int j = 0; j < 3 * rectangle.x_size; j+=3)
        {
            if (pixel[j] > color_intensity && pixel[j+1] > color_intensity && pixel[j+2] > color_intensity)
                white++;
            else not_white++;
        }
    }
    if (non_white_strictness*not_white > white)
        return 0;
    else
        return 1;
}

// returns 1 if an open standard textbox is detected on the bottom part of the top screen, 2 if a scrolling textbox (frame 1) is detected, 3 if a scrolling textbox (frame 2) is detected, 4 if a scrolling textbox (frame 3) is detected, 5 if a textbox with large letters is detected, 0 if no textbox is detected
int textbox(unsigned char *data, int wrap, rectangle_coords & top_screen)
{
    static double magnification = top_screen.magnification;
    int x_white_start = top_screen.top_left.x + std::round(magnification * 28);
    int x_white_length = (std::round(magnification * 166));
    
    // check that a 1-pixel-wide horizontal strip (below the second line) is almost white: if not, textbox is not open
    rectangle_coords bottom_white_line = { {x_white_start, static_cast<int>(top_screen.top_left.y + std::round(magnification * 183))}, x_white_length, static_cast<int>(std::round(magnification * 1))};
    if (white_rectangle(data, wrap, bottom_white_line, 1, 235) == false)
        return 0;
    
    // check that the left border of the textbox is white: if yes, textbox is not open
    rectangle_coords left_border = { {top_screen.top_left.x, static_cast<int>(top_screen.top_left.y + std::round(magnification * 144))}, static_cast<int>(std::round(magnification * 8)), static_cast<int>(top_screen.y_size - std::round(magnification * 144))};
    if (white_rectangle(data, wrap, left_border, 1, 235) == true)
        return 0;
    
    // check that the right border of the textbox is white: if yes, textbox is not open
    rectangle_coords right_border = { {static_cast<int>(top_screen.top_left.x + top_screen.x_size - std::round(magnification * 8)), static_cast<int>(top_screen.top_left.y + std::round(magnification * 144))}, static_cast<int>(std::round(magnification * 8)), static_cast<int>(top_screen.y_size - std::round(magnification * 144))};
    if (white_rectangle(data, wrap, right_border, 1, 235) == true)
        return 0;
    
    // check that a 1-pixel-wide horizontal strip (between the two lines of text) is white
    rectangle_coords mid_white_line = { {x_white_start, static_cast<int>(top_screen.top_left.y + std::round(magnification * 168))}, x_white_length, static_cast<int>(std::round(magnification * 1))};
    if (white_rectangle(data, wrap, mid_white_line, 50, 225) == false)
    {
        // 2-pixel-wide horizontal strip (below the second line)
        rectangle_coords extra_bottom_white_line = { {x_white_start, static_cast<int>(top_screen.top_left.y + std::round(magnification * 182))}, x_white_length, static_cast<int>(std::round(magnification * 2))};
        // 1-pixel-wide horizontal strip (between the two lines of text during frame 1 of a scroll)
        rectangle_coords mid_white_line_2 = { {x_white_start, static_cast<int>(top_screen.top_left.y + std::round(magnification * 164))}, x_white_length, static_cast<int>(std::round(magnification * 1))};
        // 1-pixel-wide horizontal strip (between the two lines of text during frame 2 of a scroll)
        rectangle_coords mid_white_line_3 = { {x_white_start, static_cast<int>(top_screen.top_left.y + std::round(magnification * 160))}, x_white_length, static_cast<int>(std::round(magnification * 1))};
        // 1-pixel-wide horizontal strip (between the two lines of text during frame 2 of a scroll)
        rectangle_coords mid_white_line_4 = { {x_white_start, static_cast<int>(top_screen.top_left.y + std::round(magnification * 156))}, x_white_length, static_cast<int>(std::round(magnification * 1))};
        
        if (white_rectangle(data, wrap, extra_bottom_white_line, 50, 225) == true && white_rectangle(data, wrap, mid_white_line_2, 50, 225) == true)
            return 2;
        else if (white_rectangle(data, wrap, extra_bottom_white_line, 50, 225) == true && white_rectangle(data, wrap, mid_white_line_3, 50, 225) == true)
            return 3;
        else if (white_rectangle(data, wrap, extra_bottom_white_line, 50, 225) == true && white_rectangle(data, wrap, mid_white_line_4, 50, 225) == true)
            return 4;
        else if (white_rectangle(data, wrap, mid_white_line_2, 50, 225) == false && white_rectangle(data, wrap, mid_white_line_3, 50, 225) == false && white_rectangle(data, wrap, mid_white_line_4, 50, 225) == false)
        {
            rectangle_coords top_white_line = { {x_white_start, static_cast<int>(top_screen.top_left.y + std::round(magnification * 152))}, x_white_length, static_cast<int>(std::round(magnification * 1))};
            if (white_rectangle(data, wrap, top_white_line, 50, 225) == true)
                return 5;
            else
                return 0;
        }
        else
        {
            std::cout << "MID NO, SOMETHING STRANGE" << std::endl;
            return 0;
        }
    }
    else
    {
        rectangle_coords top_white_line = { {x_white_start, static_cast<int>(top_screen.top_left.y + std::round(magnification * 152))}, x_white_length, static_cast<int>(std::round(magnification * 1))};
        if (white_rectangle(data, wrap, top_white_line, 50, 225) == true)
            return 1;
        else
        {
            std::cout << "MID YES, NO TOP" << std::endl;
            return 0;
        }
    }
}

// returns 1 the textbox is empty, 0 otherwise
bool empty_textbox(unsigned char *data, int wrap, rectangle_coords & top_screen)
{
    static double magnification = top_screen.magnification;
    
    rectangle_coords rectangle = { {static_cast<int>(top_screen.top_left.x + std::round(magnification * 13)), static_cast<int>(top_screen.top_left.y + std::round(magnification * 152))}, static_cast<int>(std::round(magnification * 220)), static_cast<int>(std::round(magnification * 33))};
    return white_rectangle(data, wrap, rectangle, 40, 235);
}

// returns true if the new textbox changed completely compared to the old one
bool compare_textboxes(unsigned char *data_old, unsigned char *data_new, int wrap, rectangle_coords & top_screen)
{
    static double magnification = top_screen.magnification;
    
    static rectangle_coords part = { {static_cast<int>(top_screen.top_left.x + std::round(magnification * 13)), static_cast<int>(top_screen.top_left.y + std::round(magnification * 152))}, static_cast<int>(std::round(magnification * 220)), static_cast<int>(std::round(magnification * 33))};
    
    unsigned char *pixel_old, *pixel_new;
    
    int changed_pixels = 0;
    int r, g, b;

    for (int i = part.top_left.y; i < part.top_left.y + part.y_size; i++)
    {
        pixel_old = data_old + i * wrap + 3 * part.top_left.x;
        pixel_new = data_new + i * wrap + 3 * part.top_left.x;
        for (int j = 0; j < 3 * part.x_size; j+=3)
        {
            if (pixel_old[j] > pixel_new[j]) r = pixel_old[j] - pixel_new[j];
            else r = pixel_new[j] - pixel_old[j];
            
            if (pixel_old[j+1] > pixel_new[j+1]) g = pixel_old[j+1] - pixel_new[j+1];
            else g = pixel_new[j+1] - pixel_old[j+1];
            
            if (pixel_old[j+2] > pixel_new[j+2]) b = pixel_old[j+2] - pixel_new[j+2];
            else b = pixel_new[j+2] - pixel_old[j+2];
            
            if (r > 50 || g > 50 || b > 50)
                changed_pixels++;
        }
    }
    
    std::cout << "changed_pixels = " << changed_pixels << std::endl;
    
    if (changed_pixels > 300 * magnification * magnification)
        return 1;
    else
        return 0;
}

char * read_text(tesseract::TessBaseAPI *api)
{
    char *text;
    
    // Open input image with leptonica library
    Pix *image = pixRead("frame.bmp");
    api->SetImage(image);
        
    // Get OCR result
    text = api->GetUTF8Text();
    //std::cout << text << std::endl;
    
    pixDestroy(&image);
    
    return text;
}

// open the input file and initialize the ffmpeg objects
int open_input_file(const char *filename) {
    int ret;
    const AVCodec *dec;
    
    // open the input file
    if ((ret = avformat_open_input(&fmt_ctx, filename, NULL, NULL)) < 0) {
        std::cout << "ERROR: failed to open input file" << std::endl;
        return ret;
    }
    
    // find stram info based on input file
    if ((ret = avformat_find_stream_info(fmt_ctx, NULL)) < 0) {
        std::cout << "ERROR: failed to find stream information" << std::endl;
        return ret;
    }
    
    // find the best video stream for the input file
    if ((ret = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, &dec, 0)) < 0) {
        std::cout << "ERROR: failed to find a video stream in the input file" << std::endl;
        return ret;
    }
        
    // allocate the decoding context for the input file
    dec_ctx = avcodec_alloc_context3(dec);
    if (!dec_ctx) {
        std::cout << "ERROR: failed to allocate decoding context" << std::endl;
        // cannot allocate memory error
        return AVERROR(ENOMEM);
    }
    
    video_stream_index = ret;
    avcodec_parameters_to_context(dec_ctx, fmt_ctx->streams[video_stream_index]->codecpar);
    
    // initialize the video decoder
    if ((ret = avcodec_open2(dec_ctx, dec, NULL)) < 0) {
        std::cout << "ERROR: failed to open video decoder" << std::endl;
        return ret;
    }
    
    return 0;
}

// save the frame as a file
// another save function that compresses to a jpg is suggested here: https://stackoverflow.com/questions/74271952/how-do-i-use-the-ffmpeg-libraries-to-extract-every-nth-frame-from-a-video-and-sa
void save(unsigned char *data, int wrap, int x_size, int y_size, char *file_name)
{
    FILE *file;
        
    file = fopen(file_name, "wb");
    fprintf(file, "P6\n%d %d\n%d\n", x_size, y_size, 255);
        
    for (int i = 0; i < y_size; i++) {
        // wrap is equal to 3 times x_size
        fwrite(data + i * wrap, 1, 3 * x_size, file);
    }
    
    fclose(file);
}

// save only the relevant part of the frame as a file
void save_textbox(unsigned char *data, int wrap, char *file_name, rectangle_coords & top_screen)
{
    FILE *file;
    unsigned char *pixel;
    
    static double magnification = top_screen.magnification;
    
    static rectangle_coords part = { {static_cast<int>(top_screen.top_left.x + std::round(magnification * 13)), static_cast<int>(top_screen.top_left.y + std::round(magnification * 152))}, static_cast<int>(std::round(magnification * 220)), static_cast<int>(std::round(magnification * 33))};
    file = fopen(file_name, "wb");
    fprintf(file, "P6\n%d %d\n%d\n", part.x_size, part.y_size, 255);
    for (int i = part.top_left.y; i < part.top_left.y + part.y_size; i++)
    {
        pixel = data + i * wrap + 3 * part.top_left.x;
        fwrite(pixel, 1, 3 * part.x_size, file);
    }
    
    fclose(file);
}

// save only the relevant part of the frame as a file
void save_second_line(unsigned char *data, int wrap, char *file_name, rectangle_coords & top_screen)
{
    FILE *file;
    unsigned char *pixel;
    
    static double magnification = top_screen.magnification;
    
    static rectangle_coords part = { {static_cast<int>(top_screen.top_left.x + std::round(magnification * 13)), static_cast<int>(top_screen.top_left.y + std::round(magnification * 168))}, static_cast<int>(std::round(magnification * 220)), static_cast<int>(std::round(magnification * 17))};
    file = fopen(file_name, "wb");
    fprintf(file, "P6\n%d %d\n%d\n", part.x_size, part.y_size, 255);
    for (int i = part.top_left.y; i < part.top_left.y + part.y_size; i++)
    {
        pixel = data + i * wrap + 3 * part.top_left.x;
        fwrite(pixel, 1, 3 * part.x_size, file);
    }
    
    fclose(file);
}

void copy_data(unsigned char *old_data, unsigned char *data, int wrap, rectangle_coords & top_screen)
{ // can be optimized by only copying the textbox
    unsigned char *old_pixel, *pixel;;
    
    static double magnification = top_screen.magnification;
    
    static rectangle_coords part = { {static_cast<int>(top_screen.top_left.x + std::round(magnification * 13)), static_cast<int>(top_screen.top_left.y + std::round(magnification * 152))}, static_cast<int>(std::round(magnification * 220)), static_cast<int>(std::round(magnification * 33))};

    for (int i = part.top_left.y; i < part.top_left.y + part.y_size; i++)
    {
        old_pixel = old_data + i * wrap + 3 * part.top_left.x;
        pixel = data + i * wrap + 3 * part.top_left.x;
        for (int j = 0; j < 3 * part.x_size; j+=3)
        {
            old_pixel[j] = pixel[j];
            old_pixel[j+1] = pixel[j+1];
            old_pixel[j+2] = pixel[j+2];
        }
    }
}

// decode frame and convert it to an RGB image
void decode(AVCodecContext *cxt, AVFrame *frame, AVFrame *rgb_frame, AVFrame *old_frame, SwsContext *sws_ctx, AVPacket *pkt, const char *out_file_name, const char *file_ext, tesseract::TessBaseAPI *api, std::ofstream & file)
{
    // define a blank char to hold the file name and an emtpy int to hold function return values
    char file_name[1024];
    int ret;
    char *text;
    
    // send packet to decoder
    ret = avcodec_send_packet(cxt, pkt);
    if (ret < 0) {
        printf("ERROR: error sending packet for decoding\n");
        exit(1);
    }
    
    static int old_textbox, new_textbox;
    
    static bool insta_textbox = 0;
    static bool only_second_line = 0;
    
    rectangle_coords top_screen;
    top_screen_coords(top_screen);
        
    while (ret >= 0) {
        // get frame back from decoder
        ret = avcodec_receive_frame(cxt, frame);
        // if "resource temp not available" or "end of file" error...
        if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) { // this can be improved. happens every other frame, no need to return the function, can just like... skip?
            return;
        } else if (ret < 0) {
            printf("ERROR: error during decoding\n");
            exit(1);
        }
        
        // output which frame is being saved
        printf("frame %03lld\n", cxt->frame_num);
        // remove temporary buffered data
        fflush(stdout);
        
        // scale (convert) the old frame to the new rgb frame
        sws_scale(sws_ctx, frame->data, frame->linesize, 0, frame->height, rgb_frame->data, rgb_frame->linesize);
        
        new_textbox = textbox(rgb_frame->data[0], rgb_frame->linesize[0], top_screen);
        
        // set "file_name" to the output file path (saves to "out_file_name_###.file_ext")
        //snprintf(file_name, sizeof(file_name), "%s_%03lld.%s", out_file_name, cxt->frame_num, file_ext);
        snprintf(file_name, sizeof(file_name), "frame.%s", file_ext);
        
        std::cout << "old_textbox = " << old_textbox << std::endl;
        std::cout << "new_textbox = " << new_textbox << std::endl;
        std::cout << "insta_textbox = " << insta_textbox << std::endl;
        std::cout << "only_second_line = " << only_second_line << std::endl;
        
        if (old_textbox == 0)
        {
            std::cout << "1 here" << std::endl;
            if (new_textbox == 1 || new_textbox == 5)
            {
                save_textbox(rgb_frame->data[0], rgb_frame->linesize[0], file_name, top_screen);
                text = read_text(api);
                std::cout << "2 here, strlen = " << strlen(text) << std::endl;
                std::cout << text << std::endl;
                if (empty_textbox(rgb_frame->data[0], rgb_frame->linesize[0], top_screen))
                    insta_textbox = false;
                else if (strlen(text) > 3)
                    insta_textbox = true;
            }
        }
        else if (old_textbox == 1 || old_textbox == 5)
        {
            if (new_textbox == 0 && insta_textbox == false)
            {
                if ( only_second_line == 0 )
                {
                    std::cout << "3 here" << std::endl;
                    save_textbox(old_frame->data[0], rgb_frame->linesize[0], file_name, top_screen);
                    text = read_text(api);
                    file << text << std::endl;
                }
                else
                {
                    std::cout << "4 here" << std::endl;
                    save_second_line(old_frame->data[0], rgb_frame->linesize[0], file_name, top_screen);
                    text = read_text(api);
                    file << text << std::endl;
                    only_second_line = 0;
                }
            }
            if ((new_textbox == 1 || new_textbox == 5) && compare_textboxes(old_frame->data[0], rgb_frame->data[0], rgb_frame->linesize[0], top_screen) && insta_textbox == false)
            {
                if ( only_second_line == 0 )
                {
                    std::cout << "5 here" << std::endl;
                    save_textbox(old_frame->data[0], rgb_frame->linesize[0], file_name, top_screen);
                    text = read_text(api);
                    file << text << std::endl;
                }
                else
                {
                    std::cout << "6 here" << std::endl;
                    save_second_line(old_frame->data[0], rgb_frame->linesize[0], file_name, top_screen);
                    text = read_text(api);
                    file << text << std::endl;
                    only_second_line = 0;
                }
                
                save_textbox(rgb_frame->data[0], rgb_frame->linesize[0], file_name, top_screen);
                text = read_text(api);
                if (empty_textbox(rgb_frame->data[0], rgb_frame->linesize[0], top_screen))
                    insta_textbox = false;
                else if (strlen(text) > 3)
                    insta_textbox = true;
            }
            if ((new_textbox == 1 || new_textbox == 5) && compare_textboxes(old_frame->data[0], rgb_frame->data[0], rgb_frame->linesize[0], top_screen) && insta_textbox == true)
            {
                insta_textbox = false;
            }
            if ((new_textbox == 2 || new_textbox == 3 || new_textbox == 4) && insta_textbox == false)
            {
                std::cout << "7 here" << std::endl;
                save_textbox(old_frame->data[0], rgb_frame->linesize[0], file_name, top_screen);
                text = read_text(api);
                file << text;
            }
        }
        else if (old_textbox == 2 || old_textbox == 3 || old_textbox == 4)
        {
            only_second_line = 1;
        }
        
        if (new_textbox == 0)
            insta_textbox = 0;
        
        copy_data(old_frame->data[0], rgb_frame->data[0], rgb_frame->linesize[0], top_screen);
        old_textbox = new_textbox;
    }
}

int main()
{
    std::ofstream file;
    file.open ("output_text.txt");
    
    tesseract::TessBaseAPI *api = new tesseract::TessBaseAPI();
    // Initialize tesseract-ocr with English, without specifying tessdata path
    if (api->Init(NULL, "eng")) { // NOTE: best results in ITA seem to be obtained setting "eng", not "ita"
        fprintf(stderr, "Could not initialize tesseract.\n");
        exit(1);
    }
    api->SetVariable("tessedit_char_blacklist","*_=+|[]");
    char input_file_name[] = "video.mp4";
    
    // define variables and ffmpeg objects
    int ret;
    AVPacket *packet;
    AVFrame *frame;
    
    // allocate frame and packet
    frame = av_frame_alloc();
    packet = av_packet_alloc();
    if (!frame || !packet) {
        fprintf(stderr, "Could not allocate frame or packet\n");
        exit(1);
    }
    
    ret = open_input_file(input_file_name);
        
    // create a scalar context for the conversion
    SwsContext *sws_ctx = sws_getContext(dec_ctx->width, dec_ctx->height, dec_ctx->pix_fmt, dec_ctx->width,
                                         dec_ctx->height, AV_PIX_FMT_RGB24, SWS_BICUBIC, NULL, NULL, NULL);
    
    // create a new rgb frame for the conversion
    AVFrame* rgb_frame = av_frame_alloc();
    rgb_frame->format = AV_PIX_FMT_RGB24;
    rgb_frame->width = dec_ctx->width;
    rgb_frame->height = dec_ctx->height;
    
    AVFrame* old_frame = av_frame_alloc();
    old_frame->format = AV_PIX_FMT_RGB24;
    old_frame->width = dec_ctx->width;
    old_frame->height = dec_ctx->height;
    
    // allocate a new buffer for the rgb conversion frame
    av_frame_get_buffer(rgb_frame, 0);
    av_frame_get_buffer(old_frame, 0);
    
    // read all packets
    while (av_read_frame(fmt_ctx, packet) >= 0) {
        // if packet index matches video index...
        if (packet->stream_index == video_stream_index) {
            // send packet to decoder and save
            std::string name = "frames/img";
            std::string ext = "bmp";
            decode(dec_ctx, frame, rgb_frame, old_frame, sws_ctx, packet, name.c_str(), ext.c_str(), api, file);
        }
        
        // unreference the packet
        av_packet_unref(packet);
    }
    
    avcodec_free_context(&dec_ctx);
    avformat_close_input(&fmt_ctx);
    av_frame_free(&frame);
    av_packet_free(&packet);
    sws_freeContext(sws_ctx);
    av_frame_free(&rgb_frame);
    av_frame_free(&old_frame);
    
    // final error catch
    if (ret < 0 && ret != AVERROR_EOF) {
        fprintf(stderr, "Error occurred: %s\n", av_err2str(ret));
        exit(1);
    }
    
    // Destroy used object and release memory
    api->End();
    delete api;
    file.close();
    
    return 0;
}
