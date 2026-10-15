#!/usr/bin/env python3
"""LoRA DPO on Qwen3.5-4B (text tower) over turn-level pairs. usage: train_dpo.py --pairs data/pairs/pairs.jsonl --out work/forkdpo_out"""
import argparse, json, os, pathlib
import torch
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig
from trl import DPOConfig, DPOTrainer

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pairs', default='data/pairs/pairs.jsonl'); ap.add_argument('--out', default='work/forkdpo_out')
    ap.add_argument('--model', default=os.environ.get('FORKDPO_MODEL', 'models/base'))
    ap.add_argument('--epochs', type=float, default=2); ap.add_argument('--lr', type=float, default=1e-5); ap.add_argument('--beta', type=float, default=0.1)
    ap.add_argument('--max-prompt-tok', type=int, default=5000); ap.add_argument('--max-completion-tok', type=int, default=1500)
    a = ap.parse_args()
    tok = AutoTokenizer.from_pretrained(a.model)
    rows = [json.loads(l) for l in open(a.pairs)]
    keep = []
    for r in rows:
        try:
            pt = len(tok(tok.apply_chat_template(r['prompt'], tokenize=False, add_generation_prompt=True)).input_ids)
            ct = max(len(tok(r['chosen'][0]['content']).input_ids), len(tok(r['rejected'][0]['content']).input_ids))
        except Exception:
            continue
        if pt <= a.max_prompt_tok and ct <= a.max_completion_tok:
            keep.append(dict(prompt=r['prompt'], chosen=r['chosen'], rejected=r['rejected']))
    print(f'pairs: {len(rows)} -> kept {len(keep)} after length filter')
    ds = Dataset.from_list(keep)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16, device_map={'': 0})
    model.config.use_cache = False
    peft_cfg = LoraConfig(task_type='CAUSAL_LM', r=16, lora_alpha=32, lora_dropout=0.05, target_modules='all-linear')
    cfg = DPOConfig(output_dir=a.out, per_device_train_batch_size=1, gradient_accumulation_steps=4,
                    num_train_epochs=a.epochs, learning_rate=a.lr, beta=a.beta, bf16=True, logging_steps=2,
                    max_length=a.max_prompt_tok + a.max_completion_tok + 64, save_strategy='no', report_to=[], gradient_checkpointing=True,
                    dataset_num_proc=4, precompute_ref_log_probs=True, lr_scheduler_type='cosine', warmup_ratio=0.1, seed=17)
    tr = DPOTrainer(model=model, args=cfg, train_dataset=ds, processing_class=tok, peft_config=peft_cfg)
    tr.train()
    tr.model.save_pretrained(pathlib.Path(a.out)/'adapter')
    tok.save_pretrained(pathlib.Path(a.out)/'adapter')
    print('adapter saved')
    hist = [x for x in tr.state.log_history if 'loss' in x]
    json.dump(hist, open(pathlib.Path(a.out)/'log_history.json','w'), indent=1)
    if hist: print('first/last loss:', hist[0].get('loss'), hist[-1].get('loss'),
                   'final margins:', hist[-1].get('rewards/margins'), 'acc:', hist[-1].get('rewards/accuracies'))
if __name__ == '__main__': main()
