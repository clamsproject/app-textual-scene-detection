import itertools

import modeling.backbones

# parameter values from the best performing models in v5.0
split_size = {5}
num_epochs = {10}
num_layers = {4}
pos_unit = {60000}
pos_enc_dim = {256}
dropouts = {0.1}
# img_enc_name = modeling.backbones.model_map.keys()
img_enc_name = {'convnext_lg', 'convnext_tiny'}

# new search space for next rounds of positional encoding experiments
pos_length = {6000000}
pos_abs_th_front = {0, 3, 5, 10}
pos_abs_th_end = {0, 3, 5, 10}
pos_vec_coeff = {0, 1, 0.75, 0.5, 0.25}  # when 0, positional encoding is not enabled
# "challenging images" from later annotation (60 videos, 2024 summer)
guids_with_challenging_images_bm = [
        "cpb-aacip-00a9ed7f2ba",
        "cpb-aacip-0ace30f582d", 
        "cpb-aacip-0ae98c2c4b2",
        "cpb-aacip-0b0c0afdb11",
        "cpb-aacip-0bb992d2e7f",
        "cpb-aacip-0c0374c6c55",
        "cpb-aacip-0c727d4cac3",
        "cpb-aacip-0c74795718b",
        "cpb-aacip-0cb2aebaeba",
        "cpb-aacip-0d74af419eb",
        "cpb-aacip-0dbb0610457",
        "cpb-aacip-0dfbaaec869",
        "cpb-aacip-0e2dc840bc6",
        "cpb-aacip-0ed7e315160",
        "cpb-aacip-0f3879e2f22",
        "cpb-aacip-0f80359ada5",
        "cpb-aacip-0f80a4f5ed2",
        "cpb-aacip-0fe3e4311e1",
        "cpb-aacip-1a365705273",
        "cpb-aacip-1b295839145",
]

guids_with_challenging_images_pbd = [
        "cpb-aacip-110-16c2ftdq",
        "cpb-aacip-120-1615dwkg",
        "cpb-aacip-120-203xsm67",
        "cpb-aacip-15-70msck27",
        "cpb-aacip-16-19s1rw84",
        "cpb-aacip-17-07tmq941",
        "cpb-aacip-17-58bg87rx",
        "cpb-aacip-17-65v6xv27",
        "cpb-aacip-17-81jhbz0g",
        "cpb-aacip-29-61djhjcx",
        "cpb-aacip-29-8380gksn",
        "cpb-aacip-41-322bvxmn",
        "cpb-aacip-41-42n5tj3d",
        "cpb-aacip-110-35gb5r94",
        "cpb-aacip-111-655dvd99",
        "cpb-aacip-120-19s1rrsp",
        "cpb-aacip-120-31qfv097",
        "cpb-aacip-120-73pvmn2q",
        "cpb-aacip-120-80ht7h8d",
        "cpb-aacip-120-8279d01c",
        "cpb-aacip-120-83xsjcb2",
        "cpb-aacip-17-88qc0md1",
        "cpb-aacip-35-36tx99h9",
        "cpb-aacip-42-78tb31b1",
        "cpb-aacip-52-84zgn1wb",
        "cpb-aacip-52-87pnw5t0",
        "cpb-aacip-55-84mkmvwx",
        "cpb-aacip-75-13905w9q",
        "cpb-aacip-75-54xgxnzg",
        "cpb-aacip-77-02q5807j",
        "cpb-aacip-77-074tnfhr",
        "cpb-aacip-77-1937qsxt",
        "cpb-aacip-77-214mx491",
        "cpb-aacip-77-24jm6zc8",
        "cpb-aacip-77-35t77b2v",
        "cpb-aacip-77-44bp0mdh",
        "cpb-aacip-77-49t1h3fv",
        "cpb-aacip-77-81jhbv89",
        "cpb-aacip-83-074tmx7h",
        "cpb-aacip-83-23612txx",
]
guids_with_challenging_images = guids_with_challenging_images_bm + guids_with_challenging_images_pbd
# this set contains 40 videos with 15328 (non-transitional) + 557 (transitional) = 15885 frames
# then updated with more annotations 19331 (non-transitional) + 801 (transitional) = 20132 frames
guids_for_fixed_validation_set = guids_with_challenging_images_pbd

block_guids_train = [
    ["cpb-aacip-254-75r7szdz"],     # always block this the most "uninteresting" video (88/882 frames annotated)
    ["cpb-aacip-254-75r7szdz"] + guids_with_challenging_images,  # evaluate the impact of the new challenging images annotation

]
block_guids_valid = [
    [                               # block all loosely-annotated videos
        "cpb-aacip-254-75r7szdz",
        "cpb-aacip-259-4j09zf95",
        "cpb-aacip-526-hd7np1xn78",
        "cpb-aacip-75-72b8h82x",
        "cpb-aacip-fe9efa663c6",
        "cpb-aacip-f5847a01db5",
        "cpb-aacip-f2a88c88d9d",
        "cpb-aacip-ec590a6761d",
        "cpb-aacip-c7c64922fcd",
        "cpb-aacip-f3fa7215348",
        "cpb-aacip-f13ae523e20",
        "cpb-aacip-e7a25f07d35",
        "cpb-aacip-ce6d5e4bd7f",
        "cpb-aacip-690722078b2",
        "cpb-aacip-e649135e6ec",
        "cpb-aacip-15-93gxdjk6",
        "cpb-aacip-512-4f1mg7h078",
        "cpb-aacip-512-4m9183583s",
        "cpb-aacip-512-4b2x34nt7g",
        "cpb-aacip-512-3n20c4tr34",
        "cpb-aacip-512-3f4kk9534t",
    ] + guids_with_challenging_images,  # also block the challenging images
    # {"cpb-aacip-254-75r7szdz"},  # effectively no block except
]
nobinning = {t: t for t in modeling.FRAME_TYPES}
binning_schemes = {
    "nobinning": nobinning,
}

prebin = list(binning_schemes.keys())

param_keys = ['split_size', 'num_epochs', 'num_layers', 'pos_length', 'pos_unit', 'dropouts', 'img_enc_name', 'pos_abs_th_front', 'pos_abs_th_end', 'pos_vec_coeff', 'block_guids_train', 'block_guids_valid', 'prebin']
l = locals()
configs = []
for vals in itertools.product(*[l[key] for key in param_keys]):
    configs.append(dict(zip(param_keys, vals)))
