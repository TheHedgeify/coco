#include <assert.h>

#include "coco.h"
#include "coco_problem.c"

/**
 * @brief Data type for transform_vars_affine.
 */
typedef struct {
  double *M, *b, *x;
} transform_vars_affine_data_t;

static void transform_vars_affine_evaluate(coco_problem_t *problem, const double *x, double *y) {
  size_t i, j;
  transform_vars_affine_data_t *data;
  coco_problem_t *inner_problem;

  data = coco_problem_transformed_get_data(problem);
  inner_problem = coco_problem_transformed_get_inner_problem(problem);

  for (i = 0; i < inner_problem->number_of_variables; ++i) {
    /* data->M has problem->number_of_variables columns and inner_problem->number_of_variables rows. */
    const double *current_row = data->M + i * problem->number_of_variables;
    data->x[i] = data->b[i];
    for (j = 0; j < problem->number_of_variables; ++j) {
      data->x[i] += x[j] * current_row[j];
    }
  }
  coco_evaluate_function(inner_problem, data->x, y);
  assert(y[0] + 1e-13 >= problem->best_value[0]);
}

static void transform_vars_affine_free(void *thing) {
  transform_vars_affine_data_t *data = thing;
  coco_free_memory(data->M);
  coco_free_memory(data->b);
  coco_free_memory(data->x);
}

/*
 * FIXMEs:
 * - Calculate new smallest/largest values of interest?
 * - Resize bounds vectors if input and output dimensions do not match
 * - problem_id and problem_name need to be adjusted
 */
/*
 * Perform an affine transformation of the variable vector:
 *
 *   x |-> Mx + b
 *
 * The matrix M is stored in row-major format.
 */
static coco_problem_t *transform_vars_affine(coco_problem_t *inner_problem,
                                               const double *M,
                                               const double *b,
                                               const size_t number_of_variables) {
  coco_problem_t *problem;
  transform_vars_affine_data_t *data;
  size_t entries_in_M;

  entries_in_M = inner_problem->number_of_variables * number_of_variables;
  data = coco_allocate_memory(sizeof(*data));
  data->M = coco_duplicate_vector(M, entries_in_M);
  data->b = coco_duplicate_vector(b, inner_problem->number_of_variables);
  data->x = coco_allocate_vector(inner_problem->number_of_variables);

  problem = coco_problem_transformed_allocate(inner_problem, data, transform_vars_affine_free);
  problem->evaluate_function = transform_vars_affine_evaluate;
  return problem;
}
