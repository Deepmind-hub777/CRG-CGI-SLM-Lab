#include "llama.h"
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

static std::string read_file(const char * path) {
    std::ifstream f(path);
    if (!f) { fprintf(stderr, "cannot open %s\n", path); std::exit(1); }
    return std::string((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
}

int main(int argc, char ** argv) {
    std::string model_path, sys_path, user_path, out_path;
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "-m") == 0 && i + 1 < argc) model_path = argv[++i];
        else if (strcmp(argv[i], "-s") == 0 && i + 1 < argc) sys_path = argv[++i];
        else if (strcmp(argv[i], "-u") == 0 && i + 1 < argc) user_path = argv[++i];
        else if (strcmp(argv[i], "-o") == 0 && i + 1 < argc) out_path = argv[++i];
    }
    if (model_path.empty() || sys_path.empty() || user_path.empty() || out_path.empty()) {
        fprintf(stderr, "usage: %s -m model.gguf -s system.txt -u user.txt -o out.bin\n", argv[0]);
        return 1;
    }

    std::string sys = read_file(sys_path.c_str());
    std::string user = read_file(user_path.c_str());
    std::string prompt = "<|im_start|>system\n" + sys + "<|im_end|>\n<|im_start|>user\n" + user + "<|im_end|>\n<|im_start|>assistant\n";

    llama_backend_init();
    llama_model_params mparams = llama_model_default_params();
    mparams.n_gpu_layers = 0;
    llama_model * model = llama_model_load_from_file(model_path.c_str(), mparams);
    if (!model) { fprintf(stderr, "load model failed\n"); return 1; }

    const llama_vocab * vocab = llama_model_get_vocab(model);
    int n_prompt = -llama_tokenize(vocab, prompt.c_str(), prompt.size(), nullptr, 0, true, true);
    std::vector<llama_token> tokens(n_prompt);
    if (llama_tokenize(vocab, prompt.c_str(), prompt.size(), tokens.data(), tokens.size(), true, true) < 0) {
        fprintf(stderr, "tokenize failed\n"); return 1;
    }

    {
        std::string tok_path = out_path + ".tokens.txt";
        FILE * ft = fopen(tok_path.c_str(), "wb");
        if (ft) {
            for (int i = 0; i < n_prompt; ++i) {
                char buf[256];
                int np = llama_token_to_piece(vocab, tokens[i], buf, sizeof(buf), 0, true);
                std::string piece(buf, np > 0 ? np : 0);
                fprintf(ft, "%d\t%s\n", i, piece.c_str());
            }
            fclose(ft);
        }
    }

    llama_context_params cparams = llama_context_default_params();
    cparams.n_ctx = n_prompt + 8;
    cparams.n_batch = n_prompt;
    cparams.n_ubatch = n_prompt;
    cparams.n_threads = 4;
    cparams.n_threads_batch = 4;
    cparams.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_DISABLED;
    cparams.no_perf = true;

    llama_context * ctx = llama_init_from_model(model, cparams);
    if (!ctx) { fprintf(stderr, "ctx failed\n"); return 1; }

    llama_batch_ext * batch = llama_batch_ext_init(ctx);
    for (int i = 0; i < n_prompt; ++i) {
        int idx = llama_batch_ext_add_token(batch, 0, tokens[i]);
        llama_pos pos = i;
        llama_batch_ext_set_pos(batch, idx, &pos);
    }

    if (llama_process(ctx, LLAMA_PROCESS_TYPE_DECODE, batch) != 0) {
        fprintf(stderr, "decode failed\n"); return 1;
    }

    int ret = llama_probe_attn(ctx, out_path.c_str());
    printf("tokens=%d probe_ret=%d out=%s\n", n_prompt, ret, out_path.c_str());

    llama_batch_ext_free(batch);
    llama_free(ctx);
    llama_model_free(model);
    llama_backend_free();
    return ret == 0 ? 0 : 1;
}
