#!/usr/bin/env python3
"""Merge a LoRA adapter (trained on Qwen3_5ForCausalLM) back into the original Qwen3_5ForConditionalGeneration
checkpoint so vLLM can serve it. usage: merge_lora.py --adapter work/forkdpo_out/adapter --out models/forkdpo"""
import argparse, os, shutil, pathlib, torch
from transformers import AutoModelForCausalLM, AutoModel, AutoConfig, AutoTokenizer
from peft import PeftModel

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default=os.environ.get('FORKDPO_MODEL', 'models/base')); ap.add_argument('--adapter', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    print('loading causal base + adapter...')
    causal = AutoModelForCausalLM.from_pretrained(a.base, dtype=torch.bfloat16)
    merged = PeftModel.from_pretrained(causal, a.adapter).merge_and_unload()
    msd = merged.state_dict()
    print('loading conditional-generation full model...')
    from transformers import Qwen3_5ForConditionalGeneration
    cond = Qwen3_5ForConditionalGeneration.from_pretrained(a.base, dtype=torch.bfloat16)
    csd = cond.state_dict()
    # key translation: try exact, then insert 'language_model.' after leading 'model.'
    updated, missed = 0, []
    for k, v in msd.items():
        cands = [k]
        if k.startswith('model.'): cands.append('model.language_model.' + k[len('model.'):])
        if k.startswith('lm_head'): cands.append(k)
        hit = next((c for c in cands if c in csd and csd[c].shape == v.shape), None)
        if hit is None: missed.append(k); continue
        csd[hit].copy_(v); updated += 1
    print(f'updated {updated} tensors; unmapped {len(missed)}')
    if missed[:5]: print('sample unmapped:', missed[:5])
    assert len(missed) < 5, 'too many unmapped tensors, mapping wrong'
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cond.save_pretrained(out, safe_serialization=True)
    for f in pathlib.Path(a.base).glob('*'):
        if f.suffix in ('.json', '.txt', '.jinja') and not (out/f.name).exists() and 'safetensors' not in f.name:
            shutil.copy(f, out/f.name)
    tok = AutoTokenizer.from_pretrained(a.base); tok.save_pretrained(out)
    print('saved to', out)
if __name__ == '__main__': main()
